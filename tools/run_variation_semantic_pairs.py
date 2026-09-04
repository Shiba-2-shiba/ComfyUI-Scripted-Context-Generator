from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.plan_variation_semantic_pairs import CONTRACT_SCHEMA, SemanticPairError, canonical_bytes, file_hash, load_json, value_hash

GENERATION_SCHEMA = "variation-semantic-pair-generation-receipt/v1"
VALIDATION_SCHEMA = "variation-semantic-pair-validation/v1"


def _record_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(record) + b"\n" for record in records)


def extract_observed_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    observed = record.get("observed_identity")
    if not isinstance(observed, Mapping):
        raise SemanticPairError("observed_identity_missing", "generated record lacks a closed observed identity")
    return dict(observed)


def _binding_was_observed(record: Mapping[str, Any], binding: Mapping[str, Any]) -> bool:
    context = record.get("final_context", record.get("context"))
    if not isinstance(context, Mapping):
        return False
    expected_row = json.loads(binding["workflow_overrides"]["1"]["json_string"])
    extras = context.get("extras", {})
    observed_subject = extras.get("source_subj_key") if isinstance(extras, Mapping) else None
    if (observed_subject or context.get("subj")) != binding["subject_key"] or context.get("loc") != binding["location_key"]:
        return False
    if context.get("costume") != expected_row.get("costume"):
        return False
    observed_actions = {context.get("action")}
    if isinstance(extras, Mapping):
        observed_actions.update({extras.get("primary_action"), extras.get("raw_pool_action")})
    return binding["action_text"] in observed_actions


def validate_generated(contract: Mapping[str, Any], baseline_records: Sequence[Mapping[str, Any]], candidate_records: Sequence[Mapping[str, Any]], receipt_hash: str) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    if len(baseline_records) != len(contract["pairs"]) or len(candidate_records) != len(contract["pairs"]):
        mismatches.append({"code": "record_count_mismatch"})
    for index, pair in enumerate(contract["pairs"]):
        if index >= len(baseline_records) or index >= len(candidate_records): break
        before, after = baseline_records[index], candidate_records[index]
        for side, record in (("baseline", before), ("candidate", after)):
            if record.get("pair_id") != pair["pair_id"] or record.get("side") != side or int(record.get("run_seed", -1)) != int(pair["run_seed"]):
                mismatches.append({"code": "record_binding_mismatch", "pair_id": pair["pair_id"], "side": side})
            try: observed = extract_observed_identity(record)
            except SemanticPairError as exc:
                mismatches.append({"code": exc.code, "pair_id": pair["pair_id"], "side": side}); continue
            if observed != pair["shared_semantic_identity"]:
                mismatches.append({"code": "observed_identity_mismatch", "pair_id": pair["pair_id"], "side": side})
        before_seeds, after_seeds = before.get("resolved_seeds"), after.get("resolved_seeds")
        if not isinstance(before_seeds, Mapping) or not isinstance(after_seeds, Mapping):
            mismatches.append({"code": "resolved_seeds_missing", "pair_id": pair["pair_id"]}); continue
        allowed = set(pair.get("allowed_seed_delta", []))
        keys = set(before_seeds) | set(after_seeds)
        illegal = sorted(key for key in keys if key not in allowed and before_seeds.get(key) != after_seeds.get(key))
        if illegal: mismatches.append({"code": "resolved_seed_mismatch", "pair_id": pair["pair_id"], "keys": illegal})
    report = {"schema_version": VALIDATION_SCHEMA, "experiment_id": contract["experiment_id"], "contract_sha256": contract["contract_sha256"], "generation_receipt_sha256": receipt_hash,
              "validated_pair_count": min(len(baseline_records), len(candidate_records)), "identity_mismatch_count": sum(item["code"] in {"observed_identity_missing", "observed_identity_mismatch"} for item in mismatches),
              "seed_mismatch_count": sum(item["code"] in {"resolved_seeds_missing", "resolved_seed_mismatch"} for item in mismatches), "record_hash_mismatch_count": sum(item["code"] == "record_binding_mismatch" for item in mismatches),
              "mismatches": mismatches, "status": "pass" if not mismatches else "fail"}
    report["validation_sha256"] = value_hash(report)
    return report


def _subprocess_executor(root: Path, workflow: Path, profile: Path, pair: Mapping[str, Any], side: str) -> dict[str, Any]:
    root = root.resolve()
    workflow = workflow.resolve()
    profile = profile.resolve()
    binding = pair["intervention_binding"][side]
    runner = root / "tools" / "run_variation_semantic_pairs.py"
    if not runner.is_file(): raise SemanticPairError("candidate_runner_missing", "side root does not own the semantic pair runner", side=side, path=str(runner))
    command = [sys.executable, str(runner), "--execute-one", "--workflow", str(workflow), "--profile", str(profile), "--seed", str(pair["run_seed"]), "--overrides-json", json.dumps(binding["workflow_overrides"], separators=(",", ":"))]
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode != 0: raise SemanticPairError("side_execution_failed", "isolated semantic pair generation failed", side=side, returncode=completed.returncode, stderr_sha256=hashlib.sha256(completed.stderr.encode()).hexdigest())
    return json.loads(completed.stdout)


def run_pairs(*, contract_path: Path, baseline_root: Path, candidate_root: Path, workflow_relative: Path, profile_relative: Path, baseline_records_path: Path, candidate_records_path: Path, executor: Callable[[Path, Path, Path, Mapping[str, Any], str], dict[str, Any]] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = load_json(contract_path, CONTRACT_SCHEMA)
    body = {key: value for key, value in contract.items() if key != "contract_sha256"}
    if value_hash(body) != contract.get("contract_sha256"): raise SemanticPairError("contract_hash_mismatch", "semantic pair contract bytes drifted")
    execute = executor or _subprocess_executor
    records = {"baseline": [], "candidate": []}; pair_receipts = []
    for pair in contract["pairs"]:
        input_hash = value_hash({"pair_id": pair["pair_id"], "run_seed": pair["run_seed"], "bindings": pair["intervention_binding"]})
        made = {}
        for side, root in (("baseline", baseline_root), ("candidate", candidate_root)):
            record = execute(root, root / workflow_relative, root / profile_relative, pair, side)
            binding = pair["intervention_binding"][side]
            observed_identity = pair["shared_semantic_identity"] if _binding_was_observed(record, binding) else {"binding_mismatch": True}
            record.update({"pair_id": pair["pair_id"], "side": side, "input_sha256": input_hash, "observed_identity": observed_identity})
            records[side].append(record); made[side] = record
        pair_receipts.append({"pair_id": pair["pair_id"], "run_seed": pair["run_seed"], "input_sha256": input_hash, "baseline_record_sha256": value_hash(made["baseline"]), "candidate_record_sha256": value_hash(made["candidate"]), "baseline_resolved_seeds_sha256": value_hash(made["baseline"].get("resolved_seeds")), "candidate_resolved_seeds_sha256": value_hash(made["candidate"].get("resolved_seeds"))})
    baseline_bytes, candidate_bytes = _record_bytes(records["baseline"]), _record_bytes(records["candidate"])
    baseline_records_path.write_bytes(baseline_bytes); candidate_records_path.write_bytes(candidate_bytes)
    receipt = {"schema_version": GENERATION_SCHEMA, "experiment_id": contract["experiment_id"], "contract_path": str(contract_path), "contract_sha256": contract["contract_sha256"], "runner_path": str(Path(__file__).resolve()), "runner_sha256": file_hash(Path(__file__).resolve()),
               "workflow": {"path": str(workflow_relative), "baseline_sha256": file_hash(baseline_root / workflow_relative), "candidate_sha256": file_hash(candidate_root / workflow_relative)}, "profile": {"path": str(profile_relative), "baseline_sha256": file_hash(baseline_root / profile_relative), "candidate_sha256": file_hash(candidate_root / profile_relative)},
               "candidate_snapshot": contract["candidate_snapshot"], "pairs": pair_receipts, "baseline_records_path": str(baseline_records_path), "baseline_records_sha256": hashlib.sha256(baseline_bytes).hexdigest(), "candidate_records_path": str(candidate_records_path), "candidate_records_sha256": hashlib.sha256(candidate_bytes).hexdigest(), "status": "generated"}
    receipt["generation_receipt_sha256"] = value_hash(receipt)
    validation = validate_generated(contract, records["baseline"], records["candidate"], receipt["generation_receipt_sha256"])
    return receipt, validation


def _execute_one(args: argparse.Namespace) -> int:
    root = Path.cwd(); sys.path.insert(0, str(root))
    from tools.workflow_prompt_runner import build_canonical_record
    from workflow_widget_validation import load_workflow
    workflow = load_workflow(Path(args.workflow)); overrides = json.loads(args.overrides_json)
    record = build_canonical_record(workflow, args.seed, Path(args.profile), overrides=overrides)
    sys.stdout.buffer.write(canonical_bytes(record)); return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--execute-one", action="store_true"); parser.add_argument("--workflow", required=True); parser.add_argument("--profile", required=True); parser.add_argument("--seed", type=int); parser.add_argument("--overrides-json")
    parser.add_argument("--contract"); parser.add_argument("--baseline-root"); parser.add_argument("--candidate-root"); parser.add_argument("--baseline-records"); parser.add_argument("--candidate-records"); parser.add_argument("--generation-receipt"); parser.add_argument("--validation-receipt")
    args = parser.parse_args(argv)
    try:
        if args.execute_one: return _execute_one(args)
        required = [args.contract, args.baseline_root, args.candidate_root, args.baseline_records, args.candidate_records, args.generation_receipt, args.validation_receipt, args.seed is None]
        if any(value is None for value in required[:-1]): raise SemanticPairError("missing_runner_argument", "paired execution arguments are incomplete")
        receipt, validation = run_pairs(contract_path=Path(args.contract), baseline_root=Path(args.baseline_root), candidate_root=Path(args.candidate_root), workflow_relative=Path(args.workflow), profile_relative=Path(args.profile), baseline_records_path=Path(args.baseline_records), candidate_records_path=Path(args.candidate_records))
        Path(args.generation_receipt).write_bytes(canonical_bytes(receipt)); Path(args.validation_receipt).write_bytes(canonical_bytes(validation)); sys.stdout.buffer.write(canonical_bytes(validation)); return 0 if validation["status"] == "pass" else 2
    except (OSError, ValueError, json.JSONDecodeError, SemanticPairError) as exc:
        error = exc if isinstance(exc, SemanticPairError) else SemanticPairError("semantic_pair_generation_failed", "semantic pair generation failed", exception_type=type(exc).__name__)
        sys.stderr.buffer.write(canonical_bytes(error.envelope())); return 2


if __name__ == "__main__": raise SystemExit(main())
