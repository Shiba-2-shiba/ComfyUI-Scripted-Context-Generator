"""Build the diagnostic R45 capability/blocker graph and R46 ranking."""
from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Iterable, Mapping
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.realizer_blocker_taxonomy import (
    blocker_domain,
    canonical_blocker_id,
    is_hard_excluded,
    is_repairable_blocker,
)
from tools.realizer_capability_projection import (
    SCHEMA_VERSION as CAPABILITY_SCHEMA,
    capability_sha256,
)
from tools.workflow_prompt_runner import canonical_json_bytes


SCHEMA = "realizer-capability-audit/v1"
OCCURRENCE_SCHEMA = "realizer-capability-occurrence/v1"
COVERAGE_SCHEMA = "realizer-coverage-signature/v1"
ROUTE_ONLY = frozenset({"family.legacy_route_ceiling"})
RESULT_FILES = (
    "capability-occurrences.jsonl",
    "capability-summary.json",
    "capability-blocker-intersections.json",
    "r46-candidates.json",
    "environment.json",
    "source-input.json",
)


def _sha256(value: Mapping) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_blockers(values: object, label: str) -> list[str]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{label} must be a list")
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"{label} entries must be strings")
        result.append(canonical_blocker_id(value))
    return sorted(set(result))


def _row_blocker_ids(row: Mapping) -> set[str]:
    result = set()
    for field in ("blockers", "errors"):
        values = row.get(field, [])
        if not isinstance(values, list):
            raise ValueError(f"row {field} must be a list")
        for value in values:
            if not isinstance(value, Mapping) or not isinstance(value.get("id"), str):
                raise ValueError(f"row {field} entries must contain string id")
            result.add(canonical_blocker_id(value["id"]))
    return result


def _family_blockers(row: Mapping) -> dict[str, list[str]]:
    signature = row.get("coverage_signature")
    if not isinstance(signature, Mapping):
        raise ValueError("coverage signature missing")
    if signature.get("schema_version") != COVERAGE_SCHEMA:
        raise ValueError("unsupported coverage signature schema")
    raw = signature.get("family_blockers")
    if not isinstance(raw, Mapping):
        raise ValueError("coverage signature family_blockers missing")
    result = {}
    for family, blockers in raw.items():
        if not isinstance(family, str) or not family:
            raise ValueError("coverage signature family key must be a non-empty string")
        result[family] = _canonical_blockers(blockers, f"family_blockers[{family}]")
    return dict(sorted(result.items()))


def _validated_projection(row: Mapping) -> Mapping:
    projection = row.get("capability_projection")
    if not isinstance(projection, Mapping):
        raise ValueError("capability projection missing")
    if projection.get("schema_version") != CAPABILITY_SCHEMA:
        raise ValueError("unsupported capability projection schema")
    if projection.get("status") not in {"AVAILABLE", "NOT_AVAILABLE"}:
        raise ValueError("unsupported capability projection status")
    projected = projection.get("capabilities")
    if not isinstance(projected, list):
        raise ValueError("capability projection capabilities must be a list")
    if projection["status"] == "NOT_AVAILABLE" and projected:
        raise ValueError("unavailable capability projection must be empty")
    return projection


def _validate_projected_capability(projected: object) -> tuple[Mapping, str]:
    if not isinstance(projected, Mapping):
        raise ValueError("projected capability must be an object")
    capability = projected.get("capability")
    sha = projected.get("capability_sha256")
    if not isinstance(capability, Mapping):
        raise ValueError("projected capability identity missing")
    if capability.get("schema_version") != CAPABILITY_SCHEMA:
        raise ValueError("unsupported capability identity schema")
    if not isinstance(capability.get("domain"), str) or not capability["domain"]:
        raise ValueError("capability domain missing")
    if not isinstance(sha, str) or capability_sha256(capability) != sha:
        raise ValueError("capability hash mismatch")
    return capability, sha


def occurrences_from_rows(rows: list[dict]) -> list[dict]:
    """Project canonical measurement context around unchanged typed identities."""
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    occurrences = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("reachability row must be an object")
        seed = row.get("run_seed")
        if type(seed) is not int:
            raise ValueError("reachability row run_seed must be an integer")
        projection = _validated_projection(row)
        family_blockers = _family_blockers(row)
        row_ids = _row_blocker_ids(row)
        all_ids = row_ids | {
            blocker for blockers in family_blockers.values() for blocker in blockers
        }
        if projection["status"] != "AVAILABLE":
            continue
        normal = row.get("normal", {})
        if not isinstance(normal, Mapping):
            raise ValueError("reachability row normal must be an object")
        for projected in projection["capabilities"]:
            capability, sha = _validate_projected_capability(projected)
            domain = capability["domain"]
            relevant = {}
            domain_ids = set()
            for family, ids in family_blockers.items():
                matching = {value for value in ids if blocker_domain(value) == domain}
                if matching:
                    relevant[family] = ids
                    domain_ids.update(matching)
            occurrences.append({
                "schema_version": OCCURRENCE_SCHEMA,
                "run_seed": seed,
                "domain": domain,
                "capability": capability,
                "capability_sha256": sha,
                "ordinary_realizer_version": normal.get("realizer_version"),
                "ordinary_syntax_family": normal.get("syntax_family"),
                "target_families": sorted(relevant),
                "blocker_ids": sorted(domain_ids),
                "family_blockers": relevant,
                "hard_excluded": any(is_hard_excluded(value) for value in all_ids),
            })
    return sorted(
        occurrences,
        key=lambda item: (
            item["run_seed"],
            item["capability_sha256"],
            canonical_json_bytes(item),
        ),
    )


def _add_raw_row_blockers(
    rows: Iterable[Mapping],
    blocker_seeds: dict[str, set[int]],
    row_family_blockers: dict[tuple[int, str], set[str]],
) -> None:
    for row in rows:
        if not isinstance(row, Mapping) or type(row.get("run_seed")) is not int:
            raise ValueError("descriptive blocker row is malformed")
        seed = row["run_seed"]
        for blocker in _row_blocker_ids(row):
            blocker_seeds[blocker].add(seed)
        for family, blockers in _family_blockers(row).items():
            blocker_seeds_for_family = row_family_blockers[(seed, family)]
            blocker_seeds_for_family.update(blockers)
            for blocker in blockers:
                blocker_seeds[blocker].add(seed)


def summarize_occurrences(
    occurrences: list[dict],
    observed_ordinary_families=(),
    *,
    rows: Iterable[Mapping] = (),
) -> dict:
    """Summarize complete seed sets while serializing only counts/examples."""
    capabilities = {}
    blocker_seeds = defaultdict(set)
    cap_blocker_seeds = defaultdict(set)
    cap_family_seeds = defaultdict(set)
    row_family_blockers = defaultdict(set)
    ordinary_families = set(observed_ordinary_families)

    for item in occurrences:
        seed = item["run_seed"]
        sha = item["capability_sha256"]
        family_keys = tuple(item.get("target_families", ()))
        record = capabilities.setdefault(sha, {
            "capability": item["capability"],
            "domain": item["domain"],
            "seed_set": set(),
            "seed_family_set": set(),
            "blocker_ids": set(),
            "family_keys": set(),
        })
        if (record["capability"] != item["capability"]
                or record["domain"] != item["domain"]):
            raise ValueError("capability hash collision or inconsistent identity")
        record["seed_set"].add(seed)
        record["blocker_ids"].update(item.get("blocker_ids", ()))
        record["family_keys"].update(family_keys)
        for family in family_keys:
            record["seed_family_set"].add((seed, family))
            cap_family_seeds[(sha, family)].add(seed)
        for blocker in item.get("blocker_ids", ()):
            blocker = canonical_blocker_id(blocker)
            blocker_seeds[blocker].add(seed)
            cap_blocker_seeds[(sha, blocker)].add(seed)
        for family, blockers in item.get("family_blockers", {}).items():
            canonical = {canonical_blocker_id(value) for value in blockers}
            row_family_blockers[(seed, family)].update(canonical)
            for blocker in canonical:
                blocker_seeds[blocker].add(seed)
                cap_blocker_seeds[(sha, blocker)].add(seed)
        if item.get("ordinary_realizer_version") == "v2" and item.get("ordinary_syntax_family"):
            ordinary_families.add(item["ordinary_syntax_family"])

    _add_raw_row_blockers(rows, blocker_seeds, row_family_blockers)

    blocker_pair_seeds = defaultdict(set)
    for (seed, _family), blockers in row_family_blockers.items():
        ordered = sorted(blockers)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                blocker_pair_seeds[(left, right)].add(seed)

    serialized_caps = {}
    for sha, value in sorted(capabilities.items()):
        serialized_caps[sha] = {
            "capability": value["capability"],
            "domain": value["domain"],
            "distinct_seed_count": len(value["seed_set"]),
            "seed_family_row_count": len(value["seed_family_set"]),
            "family_keys": sorted(value["family_keys"]),
            "blocker_ids": sorted(value["blocker_ids"]),
            "example_seeds": sorted(value["seed_set"])[:8],
        }

    return {
        "schema_version": SCHEMA,
        "ordinary_families": sorted(ordinary_families),
        "capabilities": serialized_caps,
        "blockers": {
            blocker: {
                "distinct_seed_count": len(seeds),
                "example_seeds": sorted(seeds)[:8],
            }
            for blocker, seeds in sorted(blocker_seeds.items())
        },
        "capability_blocker_intersections": [
            {
                "capability_sha256": sha,
                "blocker_id": blocker,
                "distinct_seed_count": len(seeds),
                "example_seeds": sorted(seeds)[:8],
            }
            for (sha, blocker), seeds in sorted(cap_blocker_seeds.items())
        ],
        "capability_family_intersections": [
            {
                "capability_sha256": sha,
                "family": family,
                "distinct_seed_count": len(seeds),
                "example_seeds": sorted(seeds)[:8],
            }
            for (sha, family), seeds in sorted(cap_family_seeds.items())
        ],
        "blocker_pairs": [
            {
                "blocker_ids": [left, right],
                "distinct_seed_count": len(seeds),
                "example_seeds": sorted(seeds)[:8],
            }
            for (left, right), seeds in sorted(blocker_pair_seeds.items())
        ],
    }


def rank_r46_candidates(occurrences: list[dict], summary: dict, *, limit: int = 12) -> list[dict]:
    """Rank source-bound repair work using only qualifying fallback seed unions."""
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    by_capability = defaultdict(list)
    for item in occurrences:
        if (item.get("ordinary_realizer_version") == "v1"
                and item["capability"].get("source_bound") is True
                and item.get("hard_excluded") is not True):
            by_capability[item["capability_sha256"]].append(item)

    observed = set(summary.get("ordinary_families", ()))
    ranked = []
    for sha, items in sorted(by_capability.items()):
        meta = summary.get("capabilities", {}).get(sha)
        if not isinstance(meta, Mapping):
            raise ValueError("candidate capability is missing from summary")
        domain = meta["domain"]
        affected_seeds = set()
        rescue_seeds = set()
        affected_families = set()
        blocker_ids = set()
        co_blocker_seeds = defaultdict(set)
        for item in items:
            seed = item["run_seed"]
            for family, raw_blockers in item.get("family_blockers", {}).items():
                blockers = {canonical_blocker_id(value) for value in raw_blockers}
                if any(is_hard_excluded(value) for value in blockers):
                    continue
                domain_blockers = {
                    value for value in blockers
                    if blocker_domain(value) == domain and is_repairable_blocker(value)
                }
                if not domain_blockers:
                    continue
                affected_seeds.add(seed)
                affected_families.add(family)
                blocker_ids.update(domain_blockers)
                for blocker in blockers - domain_blockers:
                    co_blocker_seeds[blocker].add(seed)
                remaining = {
                    value for value in blockers
                    if value not in ROUTE_ONLY and value not in domain_blockers
                }
                if not remaining:
                    rescue_seeds.add(seed)
        if len(affected_seeds) < 4:
            continue
        co = [
            {
                "blocker_id": blocker,
                "distinct_seed_count": len(seeds),
                "example_seeds": sorted(seeds)[:8],
            }
            for blocker, seeds in co_blocker_seeds.items()
        ]
        co.sort(key=lambda row: (-row["distinct_seed_count"], row["blocker_id"]))
        ranked.append({
            "capability_sha256": sha,
            "domain": domain,
            "capability": meta["capability"],
            "distinct_seed_count": len(affected_seeds),
            "affected_seed_count": len(affected_seeds),
            "affected_family_keys": sorted(affected_families),
            "blocker_ids": sorted(blocker_ids),
            "co_blocker_class_count": len(co),
            "top_co_blockers": co[:8],
            "single_capability_rescue_upper_bound": len(rescue_seeds),
            "example_seeds": sorted(affected_seeds)[:8],
        })

    ranked.sort(key=lambda row: (
        -row["affected_seed_count"],
        -len(set(row["affected_family_keys"]) - observed),
        row["co_blocker_class_count"],
        row["capability_sha256"],
    ))
    return [dict(row, rank=index + 1) for index, row in enumerate(ranked[:limit])]


def _validate_source_row(row: Mapping) -> None:
    signature = row.get("coverage_signature")
    projection = _validated_projection(row)
    _family_blockers(row)
    _row_blocker_ids(row)
    if type(row.get("run_seed")) is not int:
        raise ValueError("reachability row run_seed must be an integer")
    if not isinstance(signature, Mapping):
        raise ValueError("coverage signature missing")
    if row.get("coverage_signature_sha256") != _sha256(signature):
        raise ValueError("coverage signature hash mismatch")
    for projected in projection["capabilities"]:
        _validate_projected_capability(projected)
    if row.get("capability_projection_sha256") != _sha256(projection):
        raise ValueError("capability projection hash mismatch")


def _load_rows(path: Path) -> tuple[list[dict], bytes]:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read rows: {exc}") from exc
    lines = content.splitlines()
    if not lines:
        raise ValueError("rows file is empty")
    rows = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            raise ValueError(f"rows line {index} is empty")
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"rows line {index} is malformed JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"rows line {index} must be an object")
        _validate_source_row(row)
        rows.append(row)
    return rows, content


def _git_commit() -> str | None:
    command = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse"]
    top = subprocess.run(
        [*command, "--show-toplevel"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != ROOT.resolve():
        return None
    result = subprocess.run(
        [*command, "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else None


def _write_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)


def _write_outputs(
    output_dir: Path,
    rows_path: Path,
    rows: list[dict],
    rows_content: bytes,
    occurrences: list[dict],
    summary: dict,
    candidates: list[dict],
) -> None:
    conflicts = [name for name in RESULT_FILES if (output_dir / name).exists()]
    if conflicts:
        raise ValueError("output directory contains conflicting result files: " + ", ".join(conflicts))
    output_dir.mkdir(parents=True, exist_ok=True)
    git_commit = _git_commit()
    source_hashes = sorted({
        row.get("input_binding", {}).get("source_tree_hash")
        for row in rows
        if isinstance(row.get("input_binding"), Mapping)
        and isinstance(row["input_binding"].get("source_tree_hash"), str)
    })
    source_input = {
        "schema_version": "realizer-capability-audit-source/v1",
        "rows_path": rows_path.as_posix(),
        "rows_sha256": hashlib.sha256(rows_content).hexdigest(),
        "row_count": len(rows),
        "input_rows_source_tree_hashes": source_hashes,
        "audit_tool_git_commit": git_commit,
        "audit_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    environment = {
        "schema_version": "realizer-capability-audit-environment/v1",
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": sys.platform,
        "git_commit": git_commit,
    }
    intersections = {
        "schema_version": SCHEMA,
        "capability_blocker_intersections": summary["capability_blocker_intersections"],
        "capability_family_intersections": summary["capability_family_intersections"],
        "blocker_pairs": summary["blocker_pairs"],
    }
    payloads = {
        "capability-occurrences.jsonl": b"".join(canonical_json_bytes(item) for item in occurrences),
        "capability-summary.json": canonical_json_bytes(summary),
        "capability-blocker-intersections.json": canonical_json_bytes(intersections),
        "r46-candidates.json": canonical_json_bytes(candidates),
        "environment.json": canonical_json_bytes(environment),
        "source-input.json": canonical_json_bytes(source_input),
    }
    for name in RESULT_FILES:
        _write_exclusive(output_dir / name, payloads[name])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        rows, rows_content = _load_rows(args.rows)
        occurrences = occurrences_from_rows(rows)
        observed_ordinary_families = sorted({
            row.get("normal", {}).get("syntax_family")
            for row in rows
            if isinstance(row.get("normal"), Mapping)
            and row["normal"].get("realizer_version") == "v2"
            and row["normal"].get("syntax_family")
        })
        summary = summarize_occurrences(
            occurrences,
            observed_ordinary_families,
            rows=rows,
        )
        candidates = rank_r46_candidates(occurrences, summary)
        _write_outputs(
            args.output_dir,
            args.rows,
            rows,
            rows_content,
            occurrences,
            summary,
            candidates,
        )
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    sys.stdout.buffer.write(canonical_json_bytes({
        "status": "PASS",
        "output_dir": args.output_dir.as_posix(),
        "occurrence_count": len(occurrences),
        "capability_count": len(summary["capabilities"]),
        "candidate_count": len(candidates),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
