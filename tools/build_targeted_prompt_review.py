"""Build a source-isolated targeted prompt-quality repro review cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import types
import uuid
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _atomic_write(path: Path, content: bytes) -> None:
    staging = path.parent / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    temporary = staging / f"{path.name}.{uuid.uuid4().hex}.tmp"
    temporary.write_bytes(content)
    temporary.replace(path)


def _generate(mode: str, snapshot: Path, output: Path, workflow_path: Path, profile_path: Path, max_seed: int) -> None:
    if mode == "incumbent":
        module = types.ModuleType("core.solo_safety")
        module.__file__ = str(snapshot)
        module.__package__ = "core"
        exec(compile(snapshot.read_bytes(), str(snapshot), "exec"), module.__dict__)
        sys.modules["core.solo_safety"] = module

    from workflow_widget_validation import load_workflow
    from tools.workflow_prompt_runner import build_canonical_record, load_profile

    workflow = load_workflow(workflow_path)
    profile = load_profile(profile_path)
    content = b"".join(
        canonical_json_bytes(build_canonical_record(workflow, seed, profile=profile, cohort="repro_cohort"))
        for seed in range(max_seed)
    )
    _atomic_write(output, content)


def _load_records(path: Path) -> dict[int, dict[str, Any]]:
    return {int(item["run_seed"]): item for item in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def build_targeted_review(
    output_dir: Path, workflow: Path, profile: Path, max_seed: int = 256,
    review_contract_path: Path | None = None, review_attempt: int = 2,
) -> dict[str, Any]:
    if max_seed < 20 or max_seed > 2048:
        raise ValueError("bounded search range must be between 20 and 2048 seeds")
    baseline_blob = subprocess.check_output(["git", "show", "HEAD:core/solo_safety.py"], cwd=ROOT)
    baseline_manifest = json.loads(
        (ROOT / "assets/results/prompt_quality_loop/g002-baseline/source-manifest.json").read_text(encoding="utf-8")
    )
    expected_hash = next(item["sha256"] for item in baseline_manifest["entries"] if item["path"] == "core/solo_safety.py")
    baseline_content = baseline_blob
    if _hash_bytes(baseline_content) != expected_hash:
        baseline_content = baseline_blob.replace(b"\n", b"\r\n")
    baseline_hash = _hash_bytes(baseline_content)
    if baseline_hash != expected_hash:
        raise RuntimeError("HEAD solo_safety content does not match the locked g002 baseline source manifest")

    snapshot = output_dir / "provenance" / f"core_solo_safety-{baseline_hash[:16]}.py"
    _atomic_write(snapshot, baseline_content)
    staging = output_dir / ".staging"
    incumbent_search = staging / "incumbent-search.jsonl"
    candidate_search = staging / "candidate-search.jsonl"
    for mode, path in (("incumbent", incumbent_search), ("candidate", candidate_search)):
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "_generate", "--mode", mode, "--snapshot", str(snapshot),
             "--output", str(path), "--workflow", str(workflow), "--profile", str(profile), "--max-seed", str(max_seed)],
            cwd=ROOT, check=True,
        )

    incumbent, candidate = _load_records(incumbent_search), _load_records(candidate_search)
    from core.solo_safety import has_other_person_conflict

    selected = [
        seed for seed in range(max_seed)
        if has_other_person_conflict(incumbent[seed]["cleaned_prompt"])
        and not has_other_person_conflict(candidate[seed]["cleaned_prompt"])
    ][:20]
    if len(selected) != 20:
        raise RuntimeError(f"bounded search found only {len(selected)} qualifying repro seeds")

    incumbent_records = [incumbent[seed] for seed in selected]
    candidate_records = [candidate[seed] for seed in selected]
    incumbent_content = b"".join(canonical_json_bytes(item) for item in incumbent_records)
    candidate_content = b"".join(canonical_json_bytes(item) for item in candidate_records)
    _atomic_write(output_dir / "incumbent-records.jsonl", incumbent_content)
    _atomic_write(output_dir / "candidate-records.jsonl", candidate_content)

    from tools.prompt_quality_loop import build_source_manifest

    current_manifest = build_source_manifest()
    isolated_manifest = json.loads(canonical_json_bytes(current_manifest))
    isolated_manifest.pop("source_tree_hash", None)
    for entry in isolated_manifest["entries"]:
        if entry["path"] == "core/solo_safety.py":
            entry.update({"sha256": baseline_hash, "size": len(baseline_content)})
            break
    isolated_source_hash = _hash_bytes(canonical_json_bytes(isolated_manifest))
    pairs = []
    for seed in selected:
        before, after = incumbent[seed], candidate[seed]
        input_contract = {
            "base_workflow_hash": before["base_workflow_hash"],
            "config_hash": before["config_hash"],
            "profile_hash": before["profile_hash"],
            "run_seed": seed,
        }
        pairs.append({
            "candidate_conflict": False,
            "candidate_prompt_hash": _hash_bytes(after["cleaned_prompt"].encode()),
            "candidate_record_hash": _hash_bytes(canonical_json_bytes(after)),
            "incumbent_conflict": True,
            "incumbent_prompt_hash": _hash_bytes(before["cleaned_prompt"].encode()),
            "incumbent_record_hash": _hash_bytes(canonical_json_bytes(before)),
            "input_contract": input_contract,
            "input_hash": _hash_bytes(canonical_json_bytes(input_contract)),
            "run_seed": seed,
        })
    cohort_body = {
        "candidate_source_tree_hash": current_manifest["source_tree_hash"],
        "incumbent_snapshot_hash": baseline_hash,
        "incumbent_git_blob_content_hash": _hash_bytes(baseline_blob),
        "incumbent_source_tree_hash": isolated_source_hash,
        "pairs": pairs,
        "schema_version": "prompt-quality-targeted-repro-cohort/v1",
        "search_range": {"end_exclusive": max_seed, "start": 0},
    }
    cohort_body["cohort_hash"] = _hash_bytes(canonical_json_bytes(cohort_body))
    _atomic_write(output_dir / "repro-cohort.json", canonical_json_bytes(cohort_body))

    from tools.build_blind_prompt_review import build_review

    review_contract = json.loads(review_contract_path.read_text(encoding="utf-8")) if review_contract_path else {}
    review = build_review(
        output_dir / "incumbent-records.jsonl", output_dir / "candidate-records.jsonl",
        output_dir / f"review-attempt-{review_attempt:03d}", "g003-ambient-secondary-person-repro-v1", [], selected_seeds=selected,
        target_dimensions=review_contract.get("target_qualitative_dimensions"),
        guard_dimensions=review_contract.get("guard_qualitative_dimensions"),
        review_policy=json.loads((ROOT / "vocab" / "data" / "prompt_quality_policy.json").read_text(encoding="utf-8"))["review"],
    )
    incumbent_search.unlink()
    candidate_search.unlink()
    return {
        "cohort_hash": cohort_body["cohort_hash"],
        "incumbent_snapshot_hash": baseline_hash,
        "output_dir": str(output_dir),
        "review": review,
        "selected_seeds": selected,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("_generate")
    generate.add_argument("--mode", choices=("incumbent", "candidate"), required=True)
    generate.add_argument("--snapshot", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--workflow", required=True)
    generate.add_argument("--profile", required=True)
    generate.add_argument("--max-seed", type=int, required=True)
    parser.add_argument("--output-dir", default="assets/results/prompt_quality_loop/g003-repro-v1")
    parser.add_argument("--workflow", default="ComfyUI-workflow-context.json")
    parser.add_argument("--profile", default="verification/fixtures/prompt_quality_supported_profile.json")
    parser.add_argument("--max-seed", type=int, default=256)
    parser.add_argument("--review-contract")
    parser.add_argument("--review-attempt", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "_generate":
        _generate(args.mode, Path(args.snapshot), Path(args.output), Path(args.workflow), Path(args.profile), args.max_seed)
        return 0
    result = build_targeted_review(
        Path(args.output_dir), Path(args.workflow), Path(args.profile), args.max_seed,
        Path(args.review_contract) if args.review_contract else None, args.review_attempt,
    )
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
