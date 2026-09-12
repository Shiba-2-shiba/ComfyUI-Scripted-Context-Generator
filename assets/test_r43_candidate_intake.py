"""Development receipts separate actual evidence from adoption and guide targets."""
import copy
import hashlib
import json
from pathlib import Path
from unittest import mock

import pytest

from tools import realizer_candidate_intake as intake


def decisions():
    audit = {"actual": {"v2_applied_count": 10, "executed_v2_family_count": 3,
                        "observed_structure_count": 4, "errors": []}}
    preservation = {"status": "PASS", "new_ordinary_v2_count": 1}
    replay = {"families": {str(index): {"common_forced_v2": 1} for index in range(6)},
              "proof_constructor_mismatches": 0}
    return audit, preservation, replay, {"status": "PASS"}


def test_development_acceptance_is_independent_of_guide_and_adoption():
    result = intake.decide_development(*decisions())
    assert result["architecture_status"] == result["development_status"] == "PASS"
    assert result["ordinary_v2_count_512"] == 10 and result["ordinary_v2_family_count"] == 3
    assert not result["development_guide"]["met"]
    assert result["adoption_status"] == "BLOCKED"
    assert set(result["formal"].values()) == {"NOT_RUN"}


@pytest.mark.parametrize("mutation", ["ordinary", "family", "preservation", "proof", "review"])
def test_missing_development_condition_does_not_inherit_architecture_pass(mutation):
    audit, preservation, replay, review = decisions()
    if mutation == "ordinary":
        audit["actual"]["v2_applied_count"] = 9
    elif mutation == "family":
        replay["families"]["0"]["common_forced_v2"] = 0
    elif mutation == "preservation":
        preservation["status"] = "FAIL"
    elif mutation == "proof":
        replay["proof_constructor_mismatches"] = 1
    else:
        review["status"] = "NOT_RUN"
    result = intake.decide_development(audit, preservation, replay, review)
    assert result["architecture_status"] == "PASS" and result["development_status"] == "BLOCKED"
    assert result["development_blockers"] and result["adoption_status"] == "BLOCKED"


def review_fixture():
    families = {str(index): {"common_forced_v2": 1} for index in range(6)}
    replay = {"runtime_source_identity": "runtime", "families": families}
    audit = {"identity": {"workflow_hash": "workflow", "runner_config_hash": "config"}}
    entries = [{"proof": {"family": name, "eligible": True, "input_binding_sha256": "binding"},
                "forced_realizer_version": "v2", "forced_family": name, "raw": "raw", "cleaned": "clean"}
               for name in families]
    cases = [{"run_seed": 0, "family": name, "input_binding_sha256": "binding",
              "raw_sha256": hashlib.sha256(b"raw").hexdigest(), "cleaned_sha256": hashlib.sha256(b"clean").hexdigest()}
             for name in families]
    receipt = {"schema_version": "r43-development-prose-review/v1", "verdict": "PASS",
               "runtime_source_identity": "runtime", "workflow_hash": "workflow", "config_hash": "config", "cases": cases}
    return receipt, replay, [{"run_seed": 0, "families": entries}], audit, [
        {"run_seed": 0, "family": "0", "after_raw": "raw", "after_cleaned": "clean"}]


def test_review_requires_exact_current_source_input_and_prose_not_just_pass_label():
    arguments = review_fixture()
    assert intake.review_prose(*arguments)["status"] == "PASS"
    for key, changed in (("runtime_source_identity", "stale"), ("workflow_hash", "other"), ("cases", [])):
        args = copy.deepcopy(arguments)
        args[0][key] = changed
        with pytest.raises(ValueError):
            intake.review_prose(*args)
    for key in ("input_binding_sha256", "raw_sha256", "cleaned_sha256"):
        args = copy.deepcopy(arguments)
        args[0]["cases"][0][key] = "stale"
        with pytest.raises(ValueError):
            intake.review_prose(*args)
    args = copy.deepcopy(arguments)
    args[-1].append({"run_seed": 1, "family": "0"})
    with pytest.raises(ValueError):
        intake.review_prose(*args)


def test_new_ordinary_text_cannot_inherit_review_of_different_forced_text():
    for field in ("after_raw", "after_cleaned"):
        args = review_fixture()
        args[-1][0][field] = "unreviewed unrelated output"
        with pytest.raises(ValueError):
            intake.review_prose(*args)


def test_preflight_rejects_changed_supplemental_input_even_when_code_hash_matches(tmp_path):
    root, saved, output = tmp_path / "source", tmp_path / "intake", tmp_path / "preflight"
    root.mkdir()
    saved.mkdir()
    previous = {"manifest": {"source_tree_hash": "code"}, "supplemental": {"prompts.jsonl": "old"}, "a16_lock": "lock"}
    for name in intake._INTAKE_ARTIFACTS:
        path = saved / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    (saved / "source-manifest.json").write_text(json.dumps(previous))
    receipt = {"schema_version": "r43-intake/v1", "status": "PASS", "source_tree_hash": "code", "a16_lock": "lock",
               "development_guide": {"met": False}, "formal": {"gate2048": "NOT_RUN"},
               "evidence": {name: intake.file_hash(saved / name) for name in intake._INTAKE_ARTIFACTS}}
    (saved / "verdict.json").write_text(json.dumps(receipt))
    current = copy.deepcopy(previous)
    current["supplemental"]["prompts.jsonl"] = "changed"
    with mock.patch.object(intake, "source_guard", return_value=current):
        assert intake.adoption_preflight(output, root=root, intake_root=saved) == 2
    assert not output.exists()


def test_missing_baseline_and_existing_output_do_not_run_children(tmp_path):
    with mock.patch.object(intake, "run_command") as run:
        assert intake.verify_intake(tmp_path / "out", root=tmp_path) == 2
        assert not (tmp_path / "out").exists()
        sentinel = tmp_path / "out"
        sentinel.mkdir()
        (sentinel / "keep").write_text("existing")
        assert intake.verify_intake(sentinel, root=tmp_path, baseline_root=tmp_path / "absent") == 2
        assert (sentinel / "keep").read_text() == "existing"
    run.assert_not_called()


@pytest.mark.parametrize("drift", [False, True])
def test_child_failure_or_source_drift_stops_downstream_checks(tmp_path, drift):
    root, baseline, output = tmp_path / "source", tmp_path / "baseline", tmp_path / "result"
    baseline.mkdir()
    for name in ("tools/audit_realizer_reachability.py", "tools/realizer_candidate_replay.py",
                 "tools/realizer_candidate_preservation.py", intake.REVIEW_PATH):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    changed = False
    def guard(path, **kwargs):
        return {"manifest": {"source_tree_hash": "changed" if changed and Path(path) == root else "source", "entries": []},
                "supplemental": {}, "a16_lock": "lock"}
    def command(name, *args, **kwargs):
        nonlocal changed
        changed = drift
        result = {"name": name, "exit_code": 0 if drift else 1, "status": "PASS" if drift else "FAIL"}
        return result, result
    with mock.patch.object(intake, "source_guard", side_effect=guard), \
         mock.patch.object(intake, "protected_inputs", return_value={}), \
         mock.patch.object(intake, "run_command", side_effect=command) as run:
        assert intake.verify_intake(output, root=root, baseline_root=baseline) == (2 if drift else 1)
    assert run.call_count == 1
    result = intake.read_json(output / "verdict.json")
    assert result["status"] == ("INVALID" if drift else "FAIL")
    assert result["architecture_status"] == result["development_status"] == "BLOCKED"
