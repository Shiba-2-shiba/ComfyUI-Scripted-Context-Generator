"""Development measurement contracts, including non-additive blockers."""
import copy
import json
from pathlib import Path
from unittest import mock

import pytest

from tools import audit_realizer_reachability as audit


def row(seed, blockers, *, executed=False, eligible=False):
    return {
        "run_seed": seed, "builder_seed": seed + 100, "route": "fallback",
        "domains": {"action": {"binding_success": None, "grammar_known": None,
                                "runtime_available": True, "audit_only": False, "unknown": True}},
        "families": {"subject_action_scene": {
            "declared": True, "constructor_present": True, "runtime_eligible": eligible,
            "constructor_v2": None, "forced_render_v2": None, "selected": executed,
            "executed_v2": executed, "blockers": blockers}},
        "normal": {"realizer_version": "v2" if executed else "v1", "syntax_family": "subject_action_scene"},
        "blockers": [{"id": name, "kind": "unknown"} for name in blockers], "errors": [],
    }


def test_overlapping_blockers_do_not_become_individual_rescues():
    rows = [row(0, ["action.unknown"]), row(1, ["action.unknown", "scene.unknown"]),
            row(2, ["action.unknown", "scene.unknown", "template.unknown"])]
    before = copy.deepcopy(rows)
    report = audit.summarize(rows)
    assert report["blockers"]["action.unknown"]["count"] == 3
    assert report["blockers"]["action.unknown"]["only_blocked_by"] == 1
    assert report["blockers"]["scene.unknown"]["only_blocked_by"] == 0
    assert {tuple(item["blockers"]): item["count"] for item in report["blocker_pairs"]} == {
        ("action.unknown", "scene.unknown"): 2,
        ("action.unknown", "template.unknown"): 1,
        ("scene.unknown", "template.unknown"): 1,
    }
    assert report["blocker_triples"] == [{"blockers": ["action.unknown", "scene.unknown", "template.unknown"], "count": 1}]
    assert rows == before
    assert audit.summarize(list(reversed(rows))) == report


def test_unknown_forcing_and_fallback_labels_are_not_v2_success():
    report = audit.summarize([row(0, []), row(1, [], executed=True, eligible=True)])
    family = report["families"]["subject_action_scene"]
    assert family["declared"] == 2 and family["runtime_eligible"] == 1
    assert family["forced_render_v2"] == {"true": 0, "false": 0, "unknown": 2}
    assert report["actual"]["v2_applied_count"] == 1
    assert report["actual"]["v1_fallback_structure_counts"] == {"subject_action_scene": 1}
    assert report["domains"]["action"]["binding_success"] == {"true": 0, "false": 0, "unknown": 2}


def test_comparison_refuses_changed_conditions_and_detects_regression():
    record = {"run_seed": 0, "base_workflow_hash": "w", "effective_workflow_hash": "e", "config_hash": "c",
              "raw_prompt": "same", "cleaned_prompt": "same", "final_context": {"x": 1}}
    baseline = {"record": record, "builder_context": {"history": []}}
    assert audit.compare_pair(baseline, baseline)["mismatches"] == []
    changed = copy.deepcopy(baseline)
    changed["record"]["config_hash"] = "other"
    assert audit.compare_pair(baseline, changed)["status"] == "NOT_COMPARABLE"
    changed = copy.deepcopy(baseline)
    changed["record"]["raw_prompt"] = "different"
    assert audit.compare_pair(baseline, changed)["mismatches"] == ["raw_prompt"]


def test_existing_output_and_invalid_sample_count_cannot_run(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "reachability.json"
    sentinel.write_bytes(b"keep")
    with mock.patch.object(audit, "build_canonical_record") as run:
        assert audit.main(["--output-dir", str(existing)]) == 2
        assert audit.main(["--sample-count", "0", "--output-dir", str(tmp_path / "new")]) == 2
    run.assert_not_called()
    assert sentinel.read_bytes() == b"keep"


def test_mismatched_builder_seed_is_not_substituted_with_run_seed():
    record = {"run_seed": 5, "raw_prompt": "same", "final_context": {},
              "output_selectors": {"raw_prompt": {"node_id": "builder", "slot": 0}},
              "execution_trace": [{"node_id": "builder", "node_type": "ContextPromptBuilder",
                                   "function": "build_prompt_context",
                                   "inputs": {"seed": 1234, "composition_mode": True, "template": "", "context_json": "{}"}}]}
    assert audit.builder_inputs(record)["seed"] == 1234
    record["execution_trace"][0]["inputs"]["seed"] = "1234"
    with pytest.raises(ValueError, match="builder"):
        audit.builder_inputs(record)


def test_source_mutation_invalidates_an_otherwise_successful_audit(tmp_path):
    identity = audit.source_identity()
    output = tmp_path / 'changed-source'
    with mock.patch.object(audit, 'source_identity', side_effect=[identity, {**identity, 'changed': True}]):
        assert audit.main(['--sample-count', '1', '--output-dir', str(output)]) == 2
    assert json.loads((output / 'reachability.json').read_text())['status'] == 'invalid'


def test_diagnostic_error_cannot_be_hidden_as_a_normal_fallback(tmp_path):
    original = audit.diagnose_snapshot
    def broken(snapshot, **kwargs):
        result = original(snapshot, **kwargs)
        result['errors'].append({'id': 'render.proof_constructor_mismatch', 'family': 'subject_action_scene'})
        return result
    output = tmp_path / 'failed-constructor'
    with mock.patch.object(audit, 'diagnose_snapshot', side_effect=broken):
        assert audit.main(['--sample-count', '1', '--output-dir', str(output)]) == 1
    report = json.loads((output / 'reachability.json').read_text())
    assert report['status'] == 'error'
    assert report['actual']['errors'][0]['id'] == 'render.proof_constructor_mismatch'


def test_canonical_report_and_rows_ignore_output_directory_and_timing(tmp_path):
    outputs = [tmp_path / name for name in ('first', 'repeat')]
    for output in outputs:
        assert audit.main(['--sample-count', '1', '--output-dir', str(output)]) == 0
    for name in ('reachability.json', 'rows.jsonl', 'records.jsonl'):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    summary = (outputs[0] / 'reachability-summary.md').read_text()
    assert summary.count('NOT_RUN | NOT_RUN') == 6
