import json
import tempfile
import unittest
from pathlib import Path

from tools.promote_variation_candidate import ALLOWLIST, PromotionError, apply_promotion, build_preflight, canonical_bytes, file_hash, recover, value_hash


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

    def test_preflight_rejects_mixed_v4_v5_review_generation(self):
        review = json.loads(self.artifacts["review"].read_text())
        review["schema_version"] = "prompt-quality-review/v5"
        self.artifacts["review"].write_bytes(canonical_bytes(review))
        with self.assertRaises(PromotionError) as raised:
            build_preflight(active_root=self.active,candidate_root=self.candidate,snapshot_manifest_path=self.manifest,artifact_paths=self.artifacts,experiment_id=self.experiment,source_hasher=self.source,content_hasher=self.content)
        self.assertEqual(raised.exception.code, "artifact_schema_generation_mismatch")

    def test_preflight_accepts_v4_comparison_with_v6_review(self):
        comparison = json.loads(self.artifacts["semantic_comparison"].read_text())
        comparison["schema_version"] = "prompt-quality-comparison/v4"
        self.artifacts["semantic_comparison"].write_bytes(canonical_bytes(comparison))
        comparison_hash = file_hash(self.artifacts["semantic_comparison"])

        review = json.loads(self.artifacts["review"].read_text())
        review.update({"schema_version": "prompt-quality-review/v6", "comparison_artifact_hash": comparison_hash})
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


if __name__=="__main__": unittest.main()
