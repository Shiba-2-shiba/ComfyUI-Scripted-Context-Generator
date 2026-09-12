import json
import tempfile
import unittest
from pathlib import Path

from tools.plan_variation_semantic_pairs import SemanticPairError, classify_action, plan_pairs, value_hash
from tools.run_variation_semantic_pairs import run_pairs, validate_generated


class SemanticPairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.taxonomy = {"schema_version":"variation-semantic-comparator-taxonomy/v1","aliases":{"costume_theme":{"casual":"contemporary"}},"shared_defaults":{"protagonist_role":"solo_female","character_profile":"adult_female","emotion_core":"focused","emotion_intensity":"moderate","time_phase":"day","weather_class":"neutral","social_distance":"alone","progress":"midway"},"subject_classes":{"solo_female":[]},"candidate_subject_comparators":{},"candidate_location_comparators":{},"location_classes":{"indoor":[],"outdoor":[]},"review_domains":{"default":["location_action_object"]}}
        self.classifier = {"schema_version":"variation-action-semantic-classifier/v1","rules":[{"id":"inspect","verbs":["checking"],"action_family":"inspect","purpose":"task","primary_object_family":"information_or_fixture"}]}

    def tearDown(self): self.temp.cleanup()
    def write_json(self, name, value):
        path=self.root/name; path.write_text(json.dumps(value),encoding="utf-8"); return path

    def test_classifier_is_closed_and_rejects_multiple_matches(self):
        self.assertEqual(classify_action("checking a board", "calm", self.classifier)["action_family"], "inspect")
        with self.assertRaises(SemanticPairError) as raised: classify_action("walking away", "calm", self.classifier)
        self.assertEqual(raised.exception.code, "action_classification_not_unique")
        duplicate=json.loads(json.dumps(self.classifier)); duplicate["rules"].append(dict(duplicate["rules"][0], id="other"))
        with self.assertRaises(SemanticPairError): classify_action("checking a board", "calm", duplicate)

    def test_planner_is_deterministic_and_proves_19_15_20(self):
        subjects=[f"candidate-{i}" for i in range(15)]; active=[f"active-{i}" for i in range(20)]; locations=[f"new-{i}" for i in range(19)]; old=[f"old-{i}" for i in range(20)]
        self.taxonomy["subject_classes"]["solo_female"] = subjects + active
        candidate=[]; baseline=[]; cp={}; bp={}
        for i, location in enumerate(locations):
            action=f"checking fixture {i}"; candidate.append({"subj":subjects[i%15],"loc":location,"action":action,"costume":"casual","meta":{"mood":"candidate","tags":{"purpose":"work"}}}); cp[location]=[{"text":action,"load":"calm"}]
            self.taxonomy["candidate_subject_comparators"][subjects[i%15]]=active
            self.taxonomy["candidate_location_comparators"][location]=old
        cp[locations[0]].append({"text":"checking alternate fixture","load":"calm"})
        for i, location in enumerate(old):
            action=f"checking fixture {i}"; baseline.append({"subj":active[i],"loc":location,"action":action,"costume":"casual","meta":{"mood":"baseline","tags":{"purpose":"rest"}}}); bp[location]=[{"text":action,"load":"calm"}]
        self.taxonomy["location_classes"]["indoor"]=locations+old
        schedule={"schema_version":"fixture","candidate_rows":candidate,"cohort":{"control_seeds":list(range(16)),"exploration_seeds":list(range(100,104))}}
        paths={"coverage":self.write_json("coverage.json",schedule),"candidate":self.write_json("cp.json",cp),"baseline_pool":self.write_json("bp.json",bp),"taxonomy":self.write_json("taxonomy.json",self.taxonomy),"classifier":self.write_json("classifier.json",self.classifier),"automatic":self.write_json("automatic.json",{"status":"pass"}),"snapshot":self.write_json("snapshot.json",{"manifest_sha256":"a"*64}),"intent":self.write_json("intent.json",{})}
        prompts=self.root/"prompts.jsonl"; prompts.write_text("\n".join(json.dumps(row) for row in baseline)+"\n",encoding="utf-8")
        kwargs=dict(experiment_id="test",coverage_path=paths["coverage"],baseline_prompts_path=prompts,candidate_action_pools_path=paths["candidate"],baseline_action_pools_path=paths["baseline_pool"],taxonomy_path=paths["taxonomy"],classifier_path=paths["classifier"],automatic_comparison_path=paths["automatic"],candidate_snapshot={"manifest_sha256":"a"*64},data_intent_path=paths["intent"])
        first=plan_pairs(**kwargs); second=plan_pairs(**kwargs)
        self.assertEqual(first,second); self.assertEqual(first["pair_count"],20); self.assertEqual(len(first["coverage"]["candidate_locations"]),19); self.assertEqual(len(first["coverage"]["candidate_subjects"]),15)
        for pair in first["pairs"]:
            before = json.loads(pair["intervention_binding"]["baseline"]["workflow_overrides"]["1"]["json_string"])
            after = json.loads(pair["intervention_binding"]["candidate"]["workflow_overrides"]["1"]["json_string"])
            self.assertEqual(after["meta"], before["meta"])
        self.assertEqual(first["contract_sha256"],value_hash({k:v for k,v in first.items() if k!="contract_sha256"}))

    def test_validation_rejects_identity_and_nonintervention_seed_drift(self):
        identity={"x":"same"}; pair={"pair_id":"p","run_seed":7,"shared_semantic_identity":identity,"allowed_seed_delta":["1:seed"]}
        contract={"schema_version":"variation-semantic-pair-contract/v1","experiment_id":"x","contract_sha256":"h","pairs":[pair]}
        before={"pair_id":"p","side":"baseline","run_seed":7,"observed_identity":identity,"resolved_seeds":{"1:seed":1,"2:seed":4}}
        after={"pair_id":"p","side":"candidate","run_seed":7,"observed_identity":{"x":"drift"},"resolved_seeds":{"1:seed":2,"2:seed":5}}
        report=validate_generated(contract,[before],[after],"r")
        self.assertEqual(report["status"],"fail"); self.assertEqual(report["identity_mismatch_count"],1); self.assertEqual(report["seed_mismatch_count"],1)

    def test_runner_binds_record_bytes_and_receipt(self):
        override={"1":{"json_string":json.dumps({"subj":"s","loc":"l","action":"checking x","costume":"casual"})},"3":{"variation_mode":"original"}}
        binding={"subject_key":"s","location_key":"l","action_text":"checking x","workflow_overrides":override}
        pair={"pair_id":"p","run_seed":7,"shared_semantic_identity":{"x":"same"},"intervention_binding":{"baseline":binding,"candidate":binding},"allowed_seed_delta":[]}
        contract={"schema_version":"variation-semantic-pair-contract/v1","experiment_id":"x","candidate_snapshot":{},"pairs":[pair]}; contract["contract_sha256"]=value_hash(contract)
        contract_path=self.write_json("contract.json",contract); self.write_json("workflow.json",{}); self.write_json("profile.json",{})
        def executor(root,workflow,profile,pair,side): return {"run_seed":7,"resolved_seeds":{"2:seed":4},"cleaned_prompt":side,"final_context":{"subj":"s","loc":"l","action":"checking x","costume":"casual"}}
        receipt,validation=run_pairs(contract_path=contract_path,baseline_root=self.root,candidate_root=self.root,workflow_relative=Path("workflow.json"),profile_relative=Path("profile.json"),baseline_records_path=self.root/"before.jsonl",candidate_records_path=self.root/"after.jsonl",executor=executor)
        self.assertEqual(validation["status"],"pass"); self.assertEqual(receipt["schema_version"],"variation-semantic-pair-generation-receipt/v1"); self.assertEqual(receipt["status"],"generated")


if __name__ == "__main__": unittest.main()
