import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.promote_variation_candidate import ALLOWLIST, PromotionError, apply_promotion, build_preflight, canonical_bytes, default_content_hash, default_source_hash, file_hash, recover, value_hash


class VariationPromotionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); base=Path(self.temp.name); self.active=base/"active"; self.candidate=base/"candidate"; self.state=base/"state"
        self.locations=[f"new-{i}" for i in range(19)]; self.allowlist=ALLOWLIST|{f"vocab/source/action_pools/{x}.json" for x in self.locations}
        for root,text in ((self.active,"before"),(self.candidate,"after")):
            for relative in self.allowlist:
                path=root/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text+relative,encoding="utf-8")
        self.source=lambda root:value_hash({p.relative_to(root).as_posix():file_hash(p) for p in root.rglob("*") if p.is_file() and ".promotion-state" not in p.parts})
        self.content=lambda root:value_hash([{"path":p,"sha256":file_hash(root/p)} for p in sorted(self.allowlist) if (root/p).is_file()])
        self.experiment="exp"
        self.artifacts={}
        schemas={"automatic_comparison":"variation-nonselected-quality-comparison/v2","semantic_comparison":"prompt-quality-comparison/v2","review":"prompt-quality-review/v4","confirmation":"variation-v150-confirmation-bundle/v1","verification":"variation-v150-verification-receipt/v1"}
        gates=["action_pools","blind_review","browser","compatibility_review","data_validation","frontend","full_flow","prompt_quality_confirmation","python_tests","target_comparison","widgets"]
        for name,schema in schemas.items():
            value={"schema_version":schema,"experiment_id":self.experiment,"status":"pass","candidate_source_tree_sha256":self.source(self.candidate),"candidate_snapshot_content_sha256":self.content(self.candidate)}
            if name == "semantic_comparison":
                value.pop("status")  # The semantic producer exposes automatic_comparison_verdict.
            path=base/(name+".json"); path.write_bytes(canonical_bytes(value)); self.artifacts[name]=path
        semantic=json.loads(self.artifacts["semantic_comparison"].read_text()); semantic.update({"automatic_comparison_path":str(self.artifacts["automatic_comparison"].resolve()),"automatic_comparison_hash":file_hash(self.artifacts["automatic_comparison"]),"automatic_comparison_verdict":"pass","uses_output_metrics_for_selection":False}); self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(semantic))
        review=json.loads(self.artifacts["review"].read_text()); review["comparison_artifact_hash"]=file_hash(self.artifacts["semantic_comparison"]); self.artifacts["review"].write_bytes(canonical_bytes(review))
        confirmation=json.loads(self.artifacts["confirmation"].read_text()); confirmation.update({"candidate_root":str(self.candidate.resolve()),"comparison_artifact_sha256":file_hash(self.artifacts["semantic_comparison"]),"review_artifact_sha256":file_hash(self.artifacts["review"])}); self.artifacts["confirmation"].write_bytes(canonical_bytes(confirmation))
        quality_gates={}
        for gate in gates:
            evidence=base/f"{gate}-evidence.json"; evidence.write_bytes(canonical_bytes({"schema_version":"prompt-quality-verification-evidence/v2","status":"pass"}))
            direct={"target_comparison":self.artifacts["semantic_comparison"],"blind_review":self.artifacts["review"],"prompt_quality_confirmation":self.artifacts["confirmation"]}.get(gate)
            result=direct or base/f"{gate}-result.json"
            if direct is None: result.write_bytes(canonical_bytes({"schema_version":"prompt-quality-gate-result/v2","status":"pass"}))
            quality_gates[gate]={"status":"pass","evidence_path":str(evidence.resolve()),"evidence_sha256":file_hash(evidence),"result_path":str(result.resolve()),"result_sha256":file_hash(result)}
        verification=json.loads(self.artifacts["verification"].read_text()); verification.update({"candidate_root":str(self.candidate.resolve()),"comparison_artifact_sha256":file_hash(self.artifacts["semantic_comparison"]),"review_artifact_sha256":file_hash(self.artifacts["review"]),"quality_gates":quality_gates}); self.artifacts["verification"].write_bytes(canonical_bytes(verification))
        manifest={"schema_version":"variation-candidate-snapshot/v1","state":"SNAPSHOT_READY","active_source_unchanged":True,"candidate_ids":{"locations":self.locations},"changed_files":sorted(self.allowlist),"baseline_source_tree_sha256":self.source(self.active),"baseline_snapshot_content_sha256":self.content(self.active),"candidate_source_tree_sha256":self.source(self.candidate),"candidate_snapshot_content_sha256":self.content(self.candidate)}
        self.manifest=base/"manifest.json"; self.manifest.write_bytes(canonical_bytes(manifest)); self.preflight_path=base/"preflight.json"
        self.preflight=build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content); self.preflight_path.write_bytes(canonical_bytes(self.preflight))
    def tearDown(self): self.temp.cleanup()
    def generator(self,stage): pass

    def test_preflight_rejects_content_drift_even_when_source_hash_is_stubbed(self):
        (self.active/next(iter(self.allowlist))).write_text("drift",encoding="utf-8")
        with self.assertRaises(PromotionError) as raised: build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=lambda _:self.preflight["baseline_source_tree_sha256"],content_hasher=self.content)
        self.assertEqual(raised.exception.code,"active_baseline_drift")

    def test_semantic_producer_verdict_is_accepted_without_generic_status(self):
        semantic = json.loads(self.artifacts["semantic_comparison"].read_text())
        self.assertNotIn("status", semantic)
        self.assertNotIn("verdict", semantic)
        self.assertEqual(semantic["automatic_comparison_verdict"], "pass")
        self.assertEqual(self.preflight["verdict"], "promote")

    def test_semantic_missing_failed_or_contradictory_verdicts_are_rejected(self):
        original = json.loads(self.artifacts["semantic_comparison"].read_text())
        cases = [
            {key: value for key, value in original.items() if key != "automatic_comparison_verdict"},
            {**original, "automatic_comparison_verdict": "fail"},
            {**original, "status": "fail", "verdict": "pass"},
            {**original, "status": "pass", "verdict": "reject"},
        ]
        for field in ("status", "verdict", "quality_verdict", "validation_verdict"):
            for value in ("fail", "unknown", None):
                cases.append({**original, field: value})
        for semantic in cases:
            with self.subTest(verdicts={key: semantic[key] for key in (
                "status", "verdict", "quality_verdict", "validation_verdict", "automatic_comparison_verdict")
                if key in semantic}):
                self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(semantic))
                with self.assertRaises(PromotionError) as raised:
                    build_preflight(active_root=self.active, candidate_root=self.candidate,
                                    snapshot_manifest_path=self.manifest, artifact_paths=self.artifacts,
                                    experiment_id=self.experiment, source_hasher=self.source, content_hasher=self.content)
                self.assertEqual(raised.exception.code, "artifact_not_passing")
                self.assertEqual(raised.exception.details["artifact"], "semantic_comparison")

    def test_semantic_passing_metadata_does_not_replace_automatic_dag_verdict(self):
        semantic = json.loads(self.artifacts["semantic_comparison"].read_text())
        semantic.update(status="pass", verdict="pass", quality_verdict="pass", validation_verdict="pass")
        for automatic_verdict in (None, "fail"):
            with self.subTest(automatic=automatic_verdict):
                semantic.pop("automatic_comparison_verdict", None)
                if automatic_verdict is not None:
                    semantic["automatic_comparison_verdict"] = automatic_verdict
                self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(semantic))
                with self.assertRaises(PromotionError) as raised:
                    build_preflight(active_root=self.active, candidate_root=self.candidate,
                                    snapshot_manifest_path=self.manifest, artifact_paths=self.artifacts,
                                    experiment_id=self.experiment, source_hasher=self.source, content_hasher=self.content)
                self.assertEqual(raised.exception.code, "receipt_dag_link_mismatch")
                self.assertEqual(raised.exception.details["edge"], "automatic_to_semantic")

    def test_preflight_rejects_mixed_v4_v5_review_generation(self):
        review = json.loads(self.artifacts["review"].read_text())
        review["schema_version"] = "prompt-quality-review/v5"
        self.artifacts["review"].write_bytes(canonical_bytes(review))
        with self.assertRaises(PromotionError) as raised:
            build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(raised.exception.code, "artifact_schema_generation_mismatch")

    def test_preflight_accepts_v4_comparison_with_v6_review(self):
        self._assert_preflight_accepts_schema_generation(4, 6)

    def test_preflight_accepts_v5_comparison_with_v7_review(self):
        self._assert_preflight_accepts_schema_generation(5, 7)

    def test_preflight_rejects_v5_comparison_with_old_review(self):
        comparison = json.loads(self.artifacts["semantic_comparison"].read_text())
        comparison["schema_version"] = "prompt-quality-comparison/v5"
        self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(comparison))
        with self.assertRaises(PromotionError) as raised:
            build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(raised.exception.code, "artifact_schema_generation_mismatch")

    def _assert_preflight_accepts_schema_generation(self, comparison_version, review_version):
        comparison = json.loads(self.artifacts["semantic_comparison"].read_text())
        comparison["schema_version"] = f"prompt-quality-comparison/v{comparison_version}"
        self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(comparison))
        comparison_hash = file_hash(self.artifacts["semantic_comparison"])

        review = json.loads(self.artifacts["review"].read_text())
        review.update({"schema_version": f"prompt-quality-review/v{review_version}", "comparison_artifact_hash": comparison_hash})
        self.artifacts["review"].write_bytes(canonical_bytes(review))
        review_hash = file_hash(self.artifacts["review"])

        confirmation = json.loads(self.artifacts["confirmation"].read_text())
        confirmation.update({"comparison_artifact_sha256": comparison_hash, "review_artifact_sha256": review_hash})
        self.artifacts["confirmation"].write_bytes(canonical_bytes(confirmation))
        verification = json.loads(self.artifacts["verification"].read_text())
        verification.update({"comparison_artifact_sha256": comparison_hash, "review_artifact_sha256": review_hash})
        for gate_name, result_hash in (
            ("target_comparison", comparison_hash),
            ("blind_review", review_hash),
            ("prompt_quality_confirmation", file_hash(self.artifacts["confirmation"])),
        ):
            gate = verification["quality_gates"][gate_name]
            gate["result_sha256"] = result_hash
            evidence_path = Path(gate["evidence_path"])
            evidence = json.loads(evidence_path.read_text())
            evidence["result_hash"] = result_hash
            evidence_path.write_bytes(canonical_bytes(evidence))
            gate["evidence_sha256"] = file_hash(evidence_path)
        self.artifacts["verification"].write_bytes(canonical_bytes(verification))

        preflight = build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(preflight["schema_version"], "variation-v150-promotion-preflight/v1")

    def test_preflight_rejects_nonallowlisted_changed_file_and_receipt_drift(self):
        manifest=json.loads(self.manifest.read_text()); manifest["changed_files"].append("outside.txt"); bad=self.manifest.parent/"bad.json"; bad.write_bytes(canonical_bytes(manifest))
        with self.assertRaises(PromotionError) as raised: build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=bad,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(raised.exception.code,"snapshot_changed_files_not_allowlisted")
        self.artifacts["review"].write_text("{}",encoding="utf-8")
        with self.assertRaises(PromotionError): apply_promotion(preflight_path=self.preflight_path,state_dir=self.state,generator=self.generator,source_hasher=self.source,content_hasher=self.content)

    def test_each_replacement_failure_rolls_back_exactly(self):
        baseline={relative:file_hash(self.active/relative) for relative in self.allowlist}
        for index in range(1,len(self.allowlist)+1):
            state=self.state/f"case-{index}"
            result=apply_promotion(preflight_path=self.preflight_path,state_dir=state,generator=self.generator,fail_after=index,source_hasher=self.source,content_hasher=self.content)
            self.assertEqual(result["state"],"ROLLED_BACK")
            self.assertEqual({relative:file_hash(self.active/relative) for relative in self.allowlist},baseline)

    def test_rollback_failure_blocks_apply_until_recover(self):
        result=apply_promotion(preflight_path=self.preflight_path,state_dir=self.state,generator=self.generator,fail_after=1,fail_rollback=True,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(result["state"],"RECOVERY_REQUIRED")
        with self.assertRaises(PromotionError) as raised: apply_promotion(preflight_path=self.preflight_path,state_dir=self.state,generator=self.generator,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(raised.exception.code,"incomplete_journal_blocks_apply")
        recovered=recover(state_dir=self.state,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(recovered["state"],"ROLLED_BACK")

    def test_absent_before_marker_removes_new_path_on_rollback(self):
        relative=sorted(self.allowlist)[0]; (self.active/relative).unlink()
        manifest=json.loads(self.manifest.read_text()); manifest["baseline_source_tree_sha256"]=self.source(self.active); manifest["baseline_snapshot_content_sha256"]=self.content(self.active)
        self.manifest.write_bytes(canonical_bytes(manifest))
        preflight=build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.preflight_path.write_bytes(canonical_bytes(preflight))
        result=apply_promotion(preflight_path=self.preflight_path,state_dir=self.state,generator=self.generator,fail_after=1,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(result["state"],"ROLLED_BACK"); self.assertFalse((self.active/relative).exists())

    def test_success_promotes_exact_candidate_and_never_runs_generator_in_active(self):
        seen=[]
        def generator(stage): seen.append(stage); self.assertNotEqual(stage,self.active)
        result=apply_promotion(preflight_path=self.preflight_path,state_dir=self.state,generator=generator,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(result["state"],"PROMOTED"); self.assertEqual(len(seen),1)
        self.assertEqual({p:file_hash(self.active/p) for p in self.allowlist},{p:file_hash(self.candidate/p) for p in self.allowlist})

    def test_postcheck_sees_candidate_in_postcheck_and_receipt_binds_result(self):
        evidence = {"status": "pass", "checks": {"data_validation": "pass"}}
        seen = []
        def postcheck(active):
            seen.append(active)
            self.assertEqual(active, self.active)
            self.assertEqual(self.source(active), self.source(self.candidate))
            self.assertEqual(json.loads((self.state / "journal.json").read_text())["state"], "POSTCHECK")
            return evidence
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                 generator=self.generator, postcheck=postcheck,
                                 source_hasher=self.source, content_hasher=self.content)
        self.assertEqual(seen, [self.active])
        self.assertEqual(result["state"], "PROMOTED")
        journal = json.loads((self.state / "journal.json").read_text())
        self.assertEqual(journal["postcheck_result"], evidence)
        self.assertEqual(result["postcheck_result"], evidence)
        self.assertEqual(result["postcheck_result_sha256"], value_hash(evidence))
        self.assertEqual(result["journal_sha256"], file_hash(self.state / "journal.json"))
        self.assertEqual(result["promotion_receipt_sha256"], value_hash({k: v for k, v in result.items() if k != "promotion_receipt_sha256"}))

    def test_postcheck_does_not_run_before_all_replacements_complete(self):
        seen = []
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                 generator=self.generator, postcheck=lambda active: seen.append(active),
                                 fail_after=1, source_hasher=self.source, content_hasher=self.content)
        self.assertEqual(result["state"], "ROLLED_BACK")
        self.assertEqual(seen, [])

    def test_postcheck_exception_or_failed_result_rolls_back(self):
        def failure(active):
            raise RuntimeError("runtime validation failed")
        for postcheck in (failure, lambda active: {"status": "fail"}):
            with self.subTest(postcheck=postcheck):
                result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                         generator=self.generator, postcheck=postcheck,
                                         source_hasher=self.source, content_hasher=self.content)
                self.assertEqual(result["state"], "ROLLED_BACK")
                self.assertEqual(self.source(self.active), self.preflight["baseline_source_tree_sha256"])
                self.assertEqual(self.content(self.active), self.preflight["baseline_snapshot_content_sha256"])

    def test_postcheck_allowlisted_mutation_is_rejected_and_rolled_back(self):
        def mutate(active):
            (active / "prompts.jsonl").write_text("unexpected mutation", encoding="utf-8")
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                 generator=self.generator, postcheck=mutate,
                                 source_hasher=self.source, content_hasher=self.content)
        self.assertEqual(result["state"], "ROLLED_BACK")
        self.assertEqual(self.source(self.active), self.preflight["baseline_source_tree_sha256"])

    def test_postcheck_unrelated_mutation_requires_recovery_without_deleting_it(self):
        def mutate(active):
            (active / "unrelated.py").write_text("unexpected mutation", encoding="utf-8")
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                 generator=self.generator, postcheck=mutate,
                                 source_hasher=self.source, content_hasher=self.content)
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertEqual((self.active / "unrelated.py").read_text(), "unexpected mutation")
        self.assertEqual(self.content(self.active), self.preflight["baseline_snapshot_content_sha256"])

    def prepare_default_hash_fixture(self, *, include_support=True):
        for root in (self.active, self.candidate):
            (root / "README.md").write_text("verification support\n", encoding="utf-8")
        baseline = self.active.parent / "baseline"
        shutil.copytree(self.active, baseline)
        manifest_text = '{\r\n  "schema_version": "snapshot-verification-inputs/v1",\r\n  "files": ["README.md"]\r\n}\r\n'
        if include_support:
            for root in (baseline, self.candidate):
                (root / ".verification-inputs.json").write_bytes(manifest_text.encode("utf-8"))
        source = default_source_hash(self.candidate)
        content = default_content_hash(self.candidate)
        for name, path in self.artifacts.items():
            value = json.loads(path.read_text())
            value.update(candidate_source_tree_sha256=source, candidate_snapshot_content_sha256=content)
            if name == "semantic_comparison":
                value["automatic_comparison_hash"] = file_hash(self.artifacts["automatic_comparison"])
            if name == "review":
                value["comparison_artifact_hash"] = file_hash(self.artifacts["semantic_comparison"])
            if name in {"confirmation", "verification"}:
                value["comparison_artifact_sha256"] = file_hash(self.artifacts["semantic_comparison"])
                value["review_artifact_sha256"] = file_hash(self.artifacts["review"])
            if name == "verification":
                for gate in value["quality_gates"].values():
                    gate["result_sha256"] = file_hash(Path(gate["result_path"]))
            path.write_bytes(canonical_bytes(value))
        manifest = json.loads(self.manifest.read_text())
        manifest.update(
            baseline_source_tree_sha256=default_source_hash(baseline),
            baseline_snapshot_content_sha256=default_content_hash(baseline),
            candidate_source_tree_sha256=source,
            candidate_snapshot_content_sha256=content,
        )
        self.manifest.write_bytes(canonical_bytes(manifest))
        return manifest_text

    def default_preflight(self):
        preflight = build_preflight(active_root=self.active, candidate_root=self.candidate,
                                    snapshot_manifest_path=self.manifest, artifact_paths=self.artifacts,
                                    experiment_id=self.experiment)
        self.preflight_path.write_bytes(canonical_bytes(preflight))
        return preflight

    def test_default_hashes_promote_support_snapshot_without_copying_marker(self):
        manifest_text = self.prepare_default_hash_fixture()
        preflight = self.default_preflight()
        self.assertEqual(preflight["verification_input_manifest_text"], manifest_text)
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        self.assertEqual(result["state"], "PROMOTED")
        self.assertFalse((self.active / ".verification-inputs.json").exists())
        self.assertEqual((self.active / "README.md").read_text(), "verification support\n")
        self.assertEqual({p: file_hash(self.active / p) for p in self.allowlist},
                         {p: file_hash(self.candidate / p) for p in self.allowlist})

    def test_default_hashes_preserve_legacy_preflight_and_promotion(self):
        self.prepare_default_hash_fixture(include_support=False)
        preflight = self.default_preflight()
        self.assertNotIn("verification_input_manifest_text", preflight)
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        self.assertEqual(result["state"], "PROMOTED")

    def test_default_hashes_reject_active_support_drift(self):
        self.prepare_default_hash_fixture()
        self.default_preflight()
        (self.active / "README.md").write_text("changed support", encoding="utf-8")
        with self.assertRaises(PromotionError) as raised:
            apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        self.assertEqual(raised.exception.code, "active_baseline_drift")
        self.assertFalse((self.state / "journal.json").exists())

    def test_postcheck_support_mutation_is_detected_by_content_hash(self):
        self.prepare_default_hash_fixture()
        preflight = self.default_preflight()
        def mutate(active):
            (active / "README.md").write_text("changed support", encoding="utf-8")
            self.assertEqual(default_source_hash(active), preflight["candidate_source_tree_sha256"])
            return {"status": "pass"}
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state,
                                 generator=self.generator, postcheck=mutate)
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertEqual((self.active / "README.md").read_text(), "changed support")
        journal = json.loads((self.state / "journal.json").read_text())
        self.assertEqual(journal["apply_error"]["code"], "post_apply_tree_hash_mismatch")

    def test_default_hashes_recover_without_candidate_using_frozen_support_context(self):
        manifest_text = self.prepare_default_hash_fixture()
        self.default_preflight()
        before = {p: file_hash(self.active / p) for p in self.allowlist}
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator,
                                 fail_after=1, fail_rollback=True)
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        journal = json.loads((self.state / "journal.json").read_text())
        self.assertEqual(journal["verification_input_manifest_text"], manifest_text)
        shutil.rmtree(self.candidate)
        result = recover(state_dir=self.state)
        self.assertEqual(result["state"], "ROLLED_BACK")
        self.assertEqual({p: file_hash(self.active / p) for p in self.allowlist}, before)
        self.assertFalse((self.active / ".verification-inputs.json").exists())

    def test_support_context_is_bound_by_preflight_hash(self):
        self.prepare_default_hash_fixture()
        preflight = self.default_preflight()
        preflight["verification_input_manifest_text"] = '{}'
        self.preflight_path.write_bytes(canonical_bytes(preflight))
        with self.assertRaises(PromotionError) as raised:
            apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        self.assertEqual(raised.exception.code, "preflight_invalid")

    def test_default_hashes_automatic_rollback_restores_support_bound_baseline(self):
        self.prepare_default_hash_fixture()
        self.default_preflight()
        before = {p: file_hash(self.active / p) for p in self.allowlist}
        result = apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator,
                                 fail_after=len(self.allowlist))
        self.assertEqual(result["state"], "ROLLED_BACK")
        self.assertEqual({p: file_hash(self.active / p) for p in self.allowlist}, before)

    def test_recovery_rejects_changed_support_context_before_restoring_files(self):
        self.prepare_default_hash_fixture()
        self.default_preflight()
        apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator,
                        fail_after=1, fail_rollback=True)
        journal_path = self.state / "journal.json"
        journal = json.loads(journal_path.read_text())
        journal["verification_input_manifest_text"] = '{}'
        journal_path.write_bytes(canonical_bytes(journal))
        before_recovery = {p: file_hash(self.active / p) for p in self.allowlist}
        with self.assertRaises(PromotionError) as raised:
            recover(state_dir=self.state)
        self.assertEqual(raised.exception.code, "recovery_context_drift")
        self.assertEqual({p: file_hash(self.active / p) for p in self.allowlist}, before_recovery)

    def test_interrupted_postcheck_blocks_new_apply_and_can_roll_back(self):
        self.prepare_default_hash_fixture()
        self.default_preflight()
        before = {p: file_hash(self.active / p) for p in self.allowlist}
        apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        journal_path = self.state / "journal.json"
        journal = json.loads(journal_path.read_text())
        journal["state"] = "POSTCHECK"
        journal_path.write_bytes(canonical_bytes(journal))
        with self.assertRaises(PromotionError) as raised:
            apply_promotion(preflight_path=self.preflight_path, state_dir=self.state, generator=self.generator)
        self.assertEqual(raised.exception.code, "incomplete_journal_blocks_apply")
        self.assertEqual(recover(state_dir=self.state)["state"], "ROLLED_BACK")
        self.assertEqual({p: file_hash(self.active / p) for p in self.allowlist}, before)

    def test_staging_excludes_repository_metadata_and_generated_results(self):
        from tools.promote_variation_candidate import _stage

        for relative in ('.git/private', 'assets/results/runtime-output.txt', 'ComfyUI_frontend/node_modules/unused'):
            path = self.active / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('not a promotion input', encoding='utf-8')
        preflight = json.loads(self.preflight_path.read_text())
        stage = _stage(preflight, self.active, self.candidate, self.generator)
        self.addCleanup(lambda: shutil.rmtree(stage) if stage.exists() else None)
        self.assertEqual(stage.parent, self.active.parent)
        self.assertFalse((stage / '.git').exists())
        self.assertFalse((stage / 'assets/results').exists())
        self.assertFalse((stage / 'ComfyUI_frontend').exists())
        self.assertEqual({p: file_hash(stage / p) for p in self.allowlist},
                         {p: file_hash(self.candidate / p) for p in self.allowlist})


if __name__=="__main__": unittest.main()
