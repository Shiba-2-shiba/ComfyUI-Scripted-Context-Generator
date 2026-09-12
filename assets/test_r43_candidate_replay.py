"""Portable replay contracts; small real input tests never run full intake."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from tools import realizer_candidate_replay as replay


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pair():
    from core.context_codec import context_from_json
    from pipeline.prompt_orchestrator import build_prompt_from_context
    from nodes_prompt_cleaner import PromptCleaner
    case = json.loads((ROOT / "assets/fixtures/r43_ordinary_real_cases.json").read_text(encoding="utf-8"))["cases"][0]
    args = case["builder_inputs"]
    context = context_from_json(args["context_json"], default_seed=args["seed"])
    updated, raw = build_prompt_from_context(context, args["template"], args["composition_mode"], args["seed"])
    return {"record": {"run_seed": 0, "raw_prompt": raw,
                       "cleaned_prompt": PromptCleaner().clean(text=raw)[0],
                       "execution_trace": [{"node_type": "ContextPromptBuilder", "inputs": args}]},
            "builder_context": updated.to_dict()}


@pytest.mark.parametrize("corrupt", ["count", "duplicate", "gap", "boolean_seed", "two_builders", "missing_context", "bad_json"])
def test_malformed_pairs_fail_closed(tmp_path, pair, corrupt):
    rows = [copy.deepcopy(pair)]
    count = 1
    if corrupt == "count":
        count = 2
    elif corrupt == "duplicate":
        rows.append(copy.deepcopy(pair))
        count = 2
    elif corrupt == "gap":
        rows[0]["record"]["run_seed"] = 1
    elif corrupt == "boolean_seed":
        rows[0]["record"]["run_seed"] = False
    elif corrupt == "two_builders":
        rows[0]["record"]["execution_trace"] *= 2
    elif corrupt == "missing_context":
        del rows[0]["builder_context"]
    path = tmp_path / "pairs.jsonl"
    path.write_text("bad json" if corrupt == "bad_json" else "\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        replay.load_pairs(path, count)


def test_output_and_context_mismatch_are_rejected(pair):
    runtime = replay.import_runtime(ROOT, "root")
    for field in ("raw_prompt", "cleaned_prompt"):
        bad = copy.deepcopy(pair)
        bad["record"][field] += " stale"
        with pytest.raises(ValueError, match="mismatch"):
            replay.replay_pair(bad, runtime)
    bad = copy.deepcopy(pair)
    bad["builder_context"]["seed"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        replay.replay_pair(bad, runtime)


def test_ineligible_families_are_never_forced_and_proofs_match(pair):
    runtime = replay.import_runtime(ROOT, "root")
    original = runtime.engine.construct_family
    calls = []
    def checked(plan, evidence, proof, **kwargs):
        assert proof.eligible
        calls.append(proof.family)
        return original(plan, evidence, proof, **kwargs)
    with mock.patch.object(runtime.engine, "construct_family", side_effect=checked):
        _, row = replay.replay_pair(pair, runtime)
    eligible = {entry["proof"]["family"] for entry in row["families"] if entry["proof"]["eligible"]}
    assert eligible and set(calls) == eligible
    for entry in row["families"]:
        assert (entry["raw"] is not None) == entry["proof"]["eligible"]
    with mock.patch.object(runtime.engine, "construct_family", side_effect=lambda *args, **kwargs: (original(*args, **kwargs)[0], ("forged-rule",))):
        with pytest.raises(ValueError, match="constructor"):
            replay.replay_pair(pair, runtime)


def test_stale_binding_and_debug_proof_mismatch_are_rejected(pair):
    runtime = replay.import_runtime(ROOT, "root")
    original = runtime.realizer.realize_content_plan
    def forged(*args, **kwargs):
        raw, debug = original(*args, **kwargs)
        debug["family_proof"] = {}
        return raw, debug
    with mock.patch.object(runtime.realizer, "realize_content_plan", side_effect=forged):
        with pytest.raises(ValueError, match="proof"):
            replay.replay_pair(pair, runtime)
    with mock.patch.object(runtime.evidence, "validate_evidence_binding", return_value=True):
        with pytest.raises(ValueError, match="stale"):
            replay.replay_pair(pair, runtime)


def test_runtime_source_identity_mismatch_is_rejected(pair):
    runtime = replay.import_runtime(ROOT, "root")
    original = runtime.evidence.build_realization_evidence
    with mock.patch.object(runtime.evidence, "build_realization_evidence",
                           side_effect=lambda *args, **kwargs: replace(original(*args, **kwargs), source_identity_sha256="forged")):
        with pytest.raises(ValueError, match="identity"):
            replay.replay_pair(pair, runtime)


def test_real_root_package_replay_canonical_parity(tmp_path, pair):
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_bytes(replay.canonical_bytes(pair))
    outputs = []
    for mode, order, seed in (("root", "ascending", "7"), ("package", "reverse", "123")):
        output = tmp_path / mode
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH="unused-contamination")
        completed = subprocess.run([sys.executable, "-B", str(ROOT / "tools/realizer_candidate_replay.py"),
            "--source-root", str(ROOT), "--pairs", str(pairs), "--output-dir", str(output),
            "--import-mode", mode, "--order", order, "--sample-count", "1"],
            env=env, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        execution = json.loads((output / "execution.json").read_text())
        assert execution["ignore_environment"] == 0
        assert execution["pythonhashseed"] == seed
        assert execution["import_mode"] == mode
        assert execution["order"] == order
        assert execution["source_root_on_sys_path"] == (mode == "root")
        assert not execution["pythonpath"]
        outputs.append(output)
    for name in ("evidence.jsonl", "family-rows.jsonl", "summary.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    assert json.loads((outputs[0] / "summary.json").read_text())["status"] == "PASS"
    assert json.loads((outputs[0] / "execution.json").read_text())["hash_sentinel"] != json.loads((outputs[1] / "execution.json").read_text())["hash_sentinel"]


def test_existing_output_is_untouched(tmp_path):
    output = tmp_path / "exists"
    output.mkdir()
    sentinel = output / "summary.json"
    sentinel.write_bytes(b"preserved")
    assert replay.main(["--source-root", str(ROOT), "--pairs", str(tmp_path / "missing"),
                        "--output-dir", str(output)]) == 2
    assert sentinel.read_bytes() == b"preserved"


def test_source_mutation_cannot_leave_a_passing_receipt(tmp_path):
    output = tmp_path / "receipt"
    def child(*args, **kwargs):
        output.mkdir()
        (output / "summary.json").write_bytes(replay.canonical_bytes({"status": "PENDING_SOURCE_GUARD"}))
        return subprocess.CompletedProcess(args[0], 0)
    with mock.patch.object(replay, "source_manifest", side_effect=[{"source_tree_hash": "before"}, {"source_tree_hash": "after"}]), \
         mock.patch.object(replay.subprocess, "run", side_effect=child):
        assert replay.main(["--source-root", str(ROOT), "--pairs", str(tmp_path / "pairs"),
                            "--output-dir", str(output)]) == 2
    assert json.loads((output / "summary.json").read_text())["status"] != "PASS"


@pytest.mark.parametrize("corruption, expected_exit", [("runtime_output", 1), ("cohort_count", 2)])
def test_cli_distinguishes_verification_failure_from_invalid_input(tmp_path, pair, corruption, expected_exit):
    if corruption == "runtime_output":
        pair["record"]["raw_prompt"] += " mismatch"
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_bytes(replay.canonical_bytes(pair))
    completed = subprocess.run([sys.executable, "-B", str(ROOT / "tools/realizer_candidate_replay.py"),
        "--source-root", str(ROOT), "--pairs", str(pairs), "--output-dir", str(tmp_path / "receipt"),
        "--sample-count", "2" if corruption == "cohort_count" else "1"], capture_output=True, text=True)
    assert completed.returncode == expected_exit, completed.stdout + completed.stderr
