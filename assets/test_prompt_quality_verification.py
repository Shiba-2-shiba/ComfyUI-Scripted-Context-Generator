import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_prompt_quality_verification import REQUIRED_GATES, build_verification
from tools.compare_prompt_quality import _verification_artifact_failures
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


class TestPromptQualityVerificationBuilder(unittest.TestCase):
    def setUp(self):
        result_root = ROOT / "assets" / "results"
        result_root.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="verification-builder-", dir=result_root))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.evidence_dir = self.root / "evidence"
        self.evidence_dir.mkdir()
        self.source_hash = "a" * 64
        self.cohort_hash = "b" * 64
        self.source_manifest_patcher = patch(
            "tools.build_prompt_quality_verification.build_source_manifest",
            return_value={"source_tree_hash": self.source_hash},
        )
        self.source_manifest = self.source_manifest_patcher.start()
        self.addCleanup(self.source_manifest_patcher.stop)
        self.comparison_path = self.root / "comparison.json"
        self.review_path = self.root / "review.json"
        self.output_path = self.root / "verification.json"
        self._write(self.comparison_path, {
            "automatic_verdict": "pass",
            "schema_version": "prompt-quality-comparison/v1",
            "source_tree_hashes": {"after": self.source_hash, "before": "c" * 64},
        })
        self._write(self.review_path, {
            "reviewed_run_provenance": {"after": {"source_tree_hash": self.source_hash}},
            "schema_version": "prompt-quality-review/v1",
            "status": "pass",
            "verdict": "pass",
        })
        self._build_confirmation_result()
        for gate_name in sorted(REQUIRED_GATES):
            if gate_name == "target_comparison":
                result_path = self.comparison_path
            elif gate_name == "blind_review":
                result_path = self.review_path
            else:
                result_path = self.evidence_dir / f"{gate_name}-result.json"
                if gate_name != "prompt_quality_confirmation":
                    self._write(result_path, {
                        "exit_code": 0,
                        "gate_name": gate_name,
                        "schema_version": "prompt-quality-gate-result/v1",
                        "source_tree_hash": self.source_hash,
                        "status": "pass",
                        "summary": self._summary(gate_name),
                    })
            self._write(self.evidence_dir / f"{gate_name}.json", {
                "command": f"verify {gate_name}",
                "exit_code": 0,
                "gate_name": gate_name,
                "result_hash": self._hash(result_path),
                "result_path": result_path.relative_to(ROOT).as_posix(),
                "schema_version": "prompt-quality-verification-evidence/v1",
                "source_tree_hash": self.source_hash,
                "status": "pass",
            })

    @staticmethod
    def _write(path, value):
        path.write_bytes(canonical_json_bytes(value))

    @staticmethod
    def _hash(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _summary(gate_name):
        summaries = {
            "action_pools": {"errors": 0, "missing_pools": 0},
            "browser": {"failures": 0, "tests_passed": 2},
            "compatibility_review": {"errors": 0, "extra_rows": 0, "missing_rows": 0},
            "data_validation": {"errors": 0, "warnings": 0},
            "frontend": {"failures": 0, "tests_passed": 4},
            "full_flow": {"checks_passed": 1, "failures": 0},
            "python_tests": {
                "errors": 0, "failures": 0, "skipped": 0,
                "tests_passed": 505, "tests_run": 505,
            },
            "widgets": {"issues": 0},
        }
        return summaries[gate_name]

    def _build_confirmation_result(self, *, source_hash=None, cohorts=None):
        source_hash = source_hash or self.source_hash
        cohorts = cohorts or {objective: self.cohort_hash for objective in ("g004", "g005", "g006")}
        bindings = {}
        for objective in ("g004", "g005", "g006"):
            artifact_path = self.root / f"{objective}-confirmation.json"
            artifact = {
                "cohort_hash": cohorts[objective],
                "comparison": {"verdict": "pass"},
                "objective": objective,
                "record_count": 256,
                "schema_version": "prompt-quality-confirmation/v1",
                "source_tree_hash": source_hash,
            }
            self._write(artifact_path, artifact)
            bindings[objective] = {
                "artifact_hash": self._hash(artifact_path),
                "artifact_path": artifact_path.relative_to(ROOT).as_posix(),
                "cohort_hash": cohorts[objective],
                "source_tree_hash": source_hash,
                "verdict": "pass",
            }
        result_path = self.evidence_dir / "prompt_quality_confirmation-result.json"
        self._write(result_path, {
            "details": {"objectives": bindings},
            "exit_code": 0,
            "gate_name": "prompt_quality_confirmation",
            "schema_version": "prompt-quality-gate-result/v1",
            "source_tree_hash": self.source_hash,
            "status": "pass",
            "summary": {"hard_gate_failures": 0, "objectives_passed": 3},
        })
        return result_path

    def _build(self):
        return build_verification(
            comparison_path=self.comparison_path,
            review_path=self.review_path,
            evidence_dir=self.evidence_dir,
            output_path=self.output_path,
        )

    def _rewrite_evidence_hash(self, gate_name, result_path):
        evidence_path = self.evidence_dir / f"{gate_name}.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["result_hash"] = self._hash(result_path)
        self._write(evidence_path, evidence)

    def _upgrade_review_to_v3(self):
        comparison = json.loads(self.comparison_path.read_text(encoding="utf-8"))
        comparison.update({
            "cohort_hashes": {"after": "1" * 64, "before": "2" * 64},
            "experiment_id": "final-v3-review",
            "qualitative_scope_hash": "3" * 64,
            "record_artifact_hashes": {"after": "4" * 64, "before": "5" * 64},
            "review_contract_hash": "6" * 64,
            "review_selection": {"selection_hash": "7" * 64},
        })
        self._write(self.comparison_path, comparison)
        review = json.loads(self.review_path.read_text(encoding="utf-8"))
        review.update({
            "comparison_artifact_hash": hashlib.sha256(canonical_json_bytes(comparison)).hexdigest(),
            "experiment_id": comparison["experiment_id"],
            "qualitative_scope_hash": comparison["qualitative_scope_hash"],
            "review_contract_hash": comparison["review_contract_hash"],
            "reviewed_record_hashes": comparison["record_artifact_hashes"],
            "reviewed_run_provenance": {
                side: {
                    "cohort_hash": comparison["cohort_hashes"][side],
                    "source_tree_hash": comparison["source_tree_hashes"][side],
                }
                for side in ("before", "after")
            },
            "schema_version": "prompt-quality-review/v3",
            "selection_hash": comparison["review_selection"]["selection_hash"],
        })
        self._write(self.review_path, review)
        self._rewrite_evidence_hash("target_comparison", self.comparison_path)
        self._rewrite_evidence_hash("blind_review", self.review_path)

    def test_builds_deterministic_exact_v2_manifest(self):
        first = self._build()
        first_bytes = self.output_path.read_bytes()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, self.output_path.read_bytes())
        self.assertEqual(set(first["quality_gates"]), REQUIRED_GATES)
        self.assertEqual(first["schema_version"], "prompt-quality-verification/v2")
        comparison = json.loads(self.comparison_path.read_text(encoding="utf-8"))
        self.assertEqual(
            first["artifacts"]["comparison_hash"],
            hashlib.sha256(canonical_json_bytes(comparison)).hexdigest(),
        )
        self.assertEqual(
            _verification_artifact_failures(
                self.output_path,
                first,
                comparison,
                self.comparison_path,
                self.review_path,
            ),
            [],
        )

    def test_accepts_current_v3_review_with_exact_comparison_binding(self):
        self._upgrade_review_to_v3()
        manifest = self._build()
        self.assertEqual(manifest["status"], "pass")

    def test_v3_comparison_cannot_fallback_to_v1_review(self):
        comparison = json.loads(self.comparison_path.read_text(encoding="utf-8"))
        comparison["review_selection"] = {"selection_hash": "7" * 64}
        self._write(self.comparison_path, comparison)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "invalid_review_artifact")

    def test_rejects_v3_review_selection_drift(self):
        self._upgrade_review_to_v3()
        review = json.loads(self.review_path.read_text(encoding="utf-8"))
        review["selection_hash"] = "8" * 64
        self._write(self.review_path, review)
        self._rewrite_evidence_hash("blind_review", self.review_path)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "invalid_review_v3_binding")

    def test_rejects_missing_or_unexpected_evidence_inventory(self):
        (self.evidence_dir / "browser.json").unlink()
        with self.assertRaisesRegex(WorkflowValidationError, "exact eleven-gate inventory") as caught:
            self._build()
        self.assertEqual(caught.exception.code, "verification_gate_inventory_invalid")

        extra_result = self.evidence_dir / "extra-result.json"
        self._write(extra_result, {})
        self._write(self.evidence_dir / "extra.json", {
            "gate_name": "extra",
            "schema_version": "prompt-quality-verification-evidence/v1",
        })
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "verification_gate_inventory_invalid")

    def test_rejects_mixed_source_and_tampered_result_hash(self):
        evidence_path = self.evidence_dir / "frontend.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["source_tree_hash"] = "d" * 64
        self._write(evidence_path, evidence)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "invalid_verification_evidence")

        evidence["source_tree_hash"] = self.source_hash
        evidence["result_hash"] = "0" * 64
        self._write(evidence_path, evidence)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "verification_result_hash_mismatch")

    def test_rejects_stale_or_changing_current_source_tree(self):
        self.source_manifest.return_value = {"source_tree_hash": "d" * 64}
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "stale_comparison_source")

        self.source_manifest.side_effect = [
            {"source_tree_hash": self.source_hash},
            {"source_tree_hash": "d" * 64},
        ]
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "source_tree_changed_during_build")

    def test_rejects_comparison_or_review_path_substitution(self):
        substitute = self.root / "substitute-comparison.json"
        shutil.copyfile(self.comparison_path, substitute)
        evidence_path = self.evidence_dir / "target_comparison.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["result_path"] = substitute.relative_to(ROOT).as_posix()
        evidence["result_hash"] = self._hash(substitute)
        self._write(evidence_path, evidence)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "verification_artifact_binding_mismatch")

    def test_rejects_stale_or_mixed_confirmation_artifacts(self):
        result_path = self._build_confirmation_result(source_hash="e" * 64)
        evidence_path = self.evidence_dir / "prompt_quality_confirmation.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["result_hash"] = self._hash(result_path)
        self._write(evidence_path, evidence)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "stale_confirmation_artifact")

        result_path = self._build_confirmation_result(cohorts={
            "g004": self.cohort_hash, "g005": "f" * 64, "g006": self.cohort_hash,
        })
        evidence["result_hash"] = self._hash(result_path)
        self._write(evidence_path, evidence)
        with self.assertRaises(WorkflowValidationError) as caught:
            self._build()
        self.assertEqual(caught.exception.code, "mixed_confirmation_cohort")


if __name__ == "__main__":
    unittest.main()
