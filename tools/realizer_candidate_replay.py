"""Replay serialized Builder inputs through existing runtime and proof engines.

The public command launches a fresh -B interpreter for the selected import mode.
Source manifests are computed in separate guard interpreters: importing the
existing manifest helper loads root runtime modules and would spoil package-mode
identity evidence if done in the replay interpreter itself.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace


class ReplayMismatch(ValueError):
    """Valid replay inputs failed a runtime verification check (exit 1)."""


def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(condition, message):
    if not condition:
        raise ReplayMismatch(message)


def builder_inputs(pair):
    builders = [row["inputs"] for row in pair["record"]["execution_trace"]
                if row.get("node_type") == "ContextPromptBuilder"]
    require(len(builders) == 1, "exactly one Builder input is required")
    builder = builders[0]
    require(isinstance(builder, dict), "Builder inputs must be an object")
    require(type(builder["seed"]) is int, "Builder seed must be an integer")
    require(isinstance(builder["template"], str), "Builder template must be text")
    require(type(builder["composition_mode"]) is bool, "Builder composition_mode must be boolean")
    require(isinstance(builder["context_json"], str) and isinstance(json.loads(builder["context_json"]), dict),
            "Builder context_json must encode an object")
    return builder


def load_pairs(path, sample_count):
    require(type(sample_count) is int and sample_count > 0, "sample count must be positive")
    pairs = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    require(len(pairs) == sample_count, "sample count mismatch")
    seeds = []
    for pair in pairs:
        require(isinstance(pair, dict) and isinstance(pair["record"], dict), "pair must contain record")
        record = pair["record"]
        require(type(record["run_seed"]) is int, "run_seed must be an integer")
        require(isinstance(record["raw_prompt"], str) and isinstance(record["cleaned_prompt"], str),
                "record prompts must be text")
        require(isinstance(pair["builder_context"], dict), "updated Builder context is required")
        builder_inputs(pair)
        seeds.append(record["run_seed"])
    require(sorted(seeds) == list(range(sample_count)), "seeds must be unique and consecutive from zero")
    return sorted(pairs, key=lambda pair: pair["record"]["run_seed"])


def import_runtime(root, mode):
    root = Path(root).resolve()
    if mode == "package":
        require(all(Path(entry or os.getcwd()).resolve() != root for entry in sys.path),
                "package replay has source root on sys.path")
        require(not any(name == "pipeline" or name.startswith("pipeline.") or name == "core" or name.startswith("core.")
                        for name in sys.modules), "package replay contains root runtime modules")
        name = "scg_candidate_replay"
        spec = importlib.util.spec_from_file_location(name, root / "__init__.py", submodule_search_locations=[str(root)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
        prefix = name + "."
    else:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        prefix = ""
    modules = {key: importlib.import_module(prefix + name) for key, name in {
        "evidence": "pipeline.realization_evidence", "engine": "pipeline.family_capabilities",
        "codec": "core.context_codec", "orchestrator": "pipeline.prompt_orchestrator",
        "realizer": "pipeline.prompt_realizer", "renderer": "prompt_renderer",
        "cleaner_module": "nodes_prompt_cleaner"}.items()}
    for module in modules.values():
        require(Path(module.__file__).resolve().is_relative_to(root), "runtime module source identity mismatch")
    return SimpleNamespace(**modules, cleaner=modules["cleaner_module"].PromptCleaner())


def replay_pair(pair, runtime):
    record, builder = pair["record"], builder_inputs(pair)
    context = runtime.codec.context_from_json(builder["context_json"], default_seed=builder["seed"])
    original, rng = copy.deepcopy(context.to_dict()), random.getstate()
    captured = []
    updated, raw = runtime.orchestrator.build_prompt_from_context(
        context, builder["template"], builder["composition_mode"], builder["seed"], audit_sink=captured.append)
    verify(raw == record["raw_prompt"] and updated.to_dict() == pair["builder_context"],
            "ordinary output/context mismatch")
    verify(runtime.cleaner.clean(text=raw)[0] == record["cleaned_prompt"], "ordinary cleaned output mismatch")
    verify(context.to_dict() == original, "received context mutation")
    verify(len(captured) == 1, "exactly one audit snapshot is required")
    snapshot = captured[0]
    inputs = snapshot["common_evidence_inputs"]
    verify(inputs["context"] == original and inputs["seed"] == builder["seed"]
            and inputs["composition_mode"] == builder["composition_mode"], "Builder input/context mismatch")
    evidence = runtime.evidence.build_realization_evidence(inputs)
    verify(evidence.source_identity_sha256 == runtime.evidence.runtime_source_identity(), "evidence source identity mismatch")
    verify(runtime.evidence.validate_evidence_binding(evidence, inputs), "evidence identity/binding mismatch")
    verify(runtime.evidence.evidence_to_dict(evidence) == snapshot["common_evidence"], "audit evidence mismatch")
    verify(set(component.domain for component in evidence.components) == set(runtime.evidence.DOMAINS),
            "evidence domain mismatch")
    stale = copy.deepcopy(inputs)
    stale["subject"] += " changed"
    verify(not runtime.evidence.validate_evidence_binding(evidence, stale), "stale evidence binding accepted")
    for component in evidence.components:
        verify(not any("adapter_not_implemented" in blocker for blocker in component.blockers), "missing evidence adapter")
        if component.runtime_available:
            verify(component.trace is not None and component.trace.input_binding_sha256 == evidence.input_binding_sha256,
                    "component trace binding mismatch")
    plan = runtime.realizer.ContentPlan(**snapshot["bridge"]["input_plan"])
    proofs = runtime.engine.prove_all_families(plan, evidence, builder_inputs=inputs)
    verify(len(proofs) == 6 and len({proof.family for proof in proofs}) == 6, "family proof coverage mismatch")
    families = []
    for proof in proofs:
        serialized = runtime.engine.family_proof_to_dict(proof)
        verify(proof.input_binding_sha256 == evidence.input_binding_sha256, "family proof evidence identity mismatch")
        row = {"proof": serialized, "forced_realizer_version": None, "forced_family": None, "raw": None, "cleaned": None}
        if proof.eligible:
            concrete, rules = runtime.engine.construct_family(plan, evidence, proof, builder_inputs=inputs)
            verify(concrete.syntax_family == proof.family and rules == proof.transform_rule_ids,
                    "proof constructor mismatch")
            requested = replace(plan, syntax_family=proof.family)
            own_proof = runtime.engine.prove_family(proof.family, requested, evidence, builder_inputs=inputs)
            verify(own_proof.eligible, "requested family proof mismatch")
            forced_raw, debug = runtime.realizer.realize_content_plan(requested, realization_evidence=evidence,
                builder_inputs=inputs, family_proof=own_proof, return_debug=True)
            verify(debug["realizer_version"] == "v2" and debug["syntax_family"] == proof.family,
                    "forced family constructor mismatch")
            verify(debug.get("family_proof") == runtime.engine.family_proof_to_dict(own_proof), "forced family proof mismatch")
            forced_raw = runtime.renderer._finalize_prompt(forced_raw, **snapshot["finalization"])
            row.update(forced_realizer_version="v2", forced_family=debug["syntax_family"], raw=forced_raw,
                       cleaned=runtime.cleaner.clean(text=forced_raw)[0])
        families.append(row)
    verify(context.to_dict() == original and random.getstate() == rng, "context/RNG mutation during replay")
    evidence_row = {"run_seed": record["run_seed"], "evidence": snapshot["common_evidence"],
                    "template_keys": [inputs["selected_templates"][part]["key"] for part in ("intro", "body", "end")],
                    "template_slots": inputs["template_slots"]}
    return evidence_row, {"run_seed": record["run_seed"], "classification": "REAL_GRAPH", "families": families}


def replay(args):
    pairs = load_pairs(args.pairs, args.sample_count)
    if args.order == "reverse":
        pairs.reverse()
    runtime = import_runtime(args.source_root, args.import_mode)
    evidence_rows, family_rows = [], []
    for index, pair in enumerate(pairs, start=1):
        evidence_row, family_row = replay_pair(pair, runtime)
        evidence_rows.append(evidence_row)
        family_rows.append(family_row)
        if index % 128 == 0 or index == len(pairs):
            print(f"Replay verified {index}/{len(pairs)} inputs", flush=True)
    evidence_rows.sort(key=lambda row: row["run_seed"])
    family_rows.sort(key=lambda row: row["run_seed"])
    evidence_data = b"".join(canonical_bytes(row) for row in evidence_rows)
    family_data = b"".join(canonical_bytes(row) for row in family_rows)
    summary = {"status": "PENDING_SOURCE_GUARD", "sample_count": len(pairs), "runtime_source_identity": runtime.evidence.runtime_source_identity(),
               "evidence_sha256": hashlib.sha256(evidence_data).hexdigest(),
               "family_rows_sha256": hashlib.sha256(family_data).hexdigest(),
               "real_graph_seed_family_rows": sum(len(row["families"]) for row in family_rows),
               "ordinary_output_context_mismatches": 0, "proof_constructor_mismatches": 0,
               "rng_mismatches": 0, "stale_bindings_rejected": len(pairs), "families": {}, "domains": {}}
    for family in sorted(item["proof"]["family"] for item in family_rows[0]["families"]):
        observations = [item for row in family_rows for item in row["families"] if item["proof"]["family"] == family]
        summary["families"][family] = {
            "common_runtime_eligible": sum(item["proof"]["eligible"] for item in observations),
            "common_forced_v2": sum(item["forced_realizer_version"] == "v2" for item in observations),
            "blockers": dict(Counter(blocker for item in observations for blocker in item["proof"]["blocker_ids"]))}
    for domain in runtime.evidence.DOMAINS:
        components = [next(item for item in row["evidence"]["components"] if item["domain"] == domain) for row in evidence_rows]
        summary["domains"][domain] = {
            "runtime_bound": sum(item["runtime_available"] and item["trace"] is not None for item in components),
            "source_trace": sum(item["trace"] is not None for item in components),
            "grammar_known": sum(bool(item["atoms"]) and all(atom["grammar_known"] == "true" for atom in item["atoms"]) for item in components),
            "blockers": dict(Counter(blocker for item in components for blocker in item["blockers"]))}
    execution = {"import_mode": args.import_mode, "order": args.order,
                 "pythonhashseed": os.environ.get("PYTHONHASHSEED"), "ignore_environment": sys.flags.ignore_environment,
                 "hash_sentinel": hash("SCG_R43_PORTABLE_REPLAY"), "pythonpath": os.environ.get("PYTHONPATH"),
                 "source_root": str(args.source_root), "pairs": str(args.pairs), "output_dir": str(args.output_dir),
                 "source_root_on_sys_path": any(Path(entry or os.getcwd()).resolve() == args.source_root for entry in sys.path)}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in (("evidence.jsonl", evidence_data), ("family-rows.jsonl", family_data),
                       ("summary.json", canonical_bytes(summary)), ("execution.json", canonical_bytes(execution))):
        (args.output_dir / name).write_bytes(data)


def source_manifest(root, env):
    code = ("import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "from tools.prompt_quality_loop import build_source_manifest; "
            "print(json.dumps(build_source_manifest(Path(sys.argv[1])),sort_keys=True))")
    result = subprocess.run([sys.executable, "-B", "-c", code, str(root)], env=env,
                            cwd=root.parent, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--import-mode", choices=("root", "package"), default="root")
    parser.add_argument("--order", choices=("ascending", "reverse"), default="ascending")
    parser.add_argument("--sample-count", type=int, default=512)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.source_root, args.pairs, args.output_dir = (value.resolve() for value in (args.source_root, args.pairs, args.output_dir))
    try:
        require(not args.output_dir.exists(), "output directory already exists")
        if args.child:
            require(sys.flags.dont_write_bytecode and not sys.flags.ignore_environment, "replay requires -B without -I/-E")
            require(not os.environ.get("PYTHONPATH"), "replay requires cleared PYTHONPATH")
            replay(args)
            return 0
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        before = source_manifest(args.source_root, env)
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child",
                   "--source-root", str(args.source_root), "--pairs", str(args.pairs), "--output-dir", str(args.output_dir),
                   "--import-mode", args.import_mode, "--order", args.order, "--sample-count", str(args.sample_count)]
        result = subprocess.run(command, env=env, cwd=args.source_root.parent)
        after = source_manifest(args.source_root, env)
        require(before == after, "source changed during replay")
        if result.returncode:
            return 1 if result.returncode == 1 else 2
        summary_path = args.output_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["status"] = "PASS"
        summary["source_tree_hash"] = before["source_tree_hash"]
        summary_path.write_bytes(canonical_bytes(summary))
        return 0
    except ReplayMismatch as error:
        print(f"Replay verification failed: {error}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        # A child receipt stays pending when the parent source guard rejects it;
        # only the public parent command can promote the receipt to PASS.
        print(f"Replay rejected: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
