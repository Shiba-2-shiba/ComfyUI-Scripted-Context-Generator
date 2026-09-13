"""Rank diagnostic R44 development packets; never grant runtime permission.

Input rows come from a current reachability audit. Their signatures describe
structural evidence, while normal.realizer_version and families.executed_v2
remain the authority for measuring ordinary execution. Projected seed counts
are upper bounds, not promised rescues or adoption thresholds.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from tools.realizer_blocker_taxonomy import (
        canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
    )
except ImportError:
    from realizer_blocker_taxonomy import (
        canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
    )

ROUTE_ONLY_EXCLUDE_IDS = frozenset({
    "family.role_mismatch", "family.composition_mode_disabled",
})
REQUIRED_FAMILIES = frozenset({
    "action_lead_subject_scene", "scene_lead_subject_action", "subject_action__scene_tail",
    "subject_action_scene", "subject_action_scene_insert", "subject_scene_action",
})


def _blocker_ids(value: Any) -> set[str]:
    """Inspect blocker/error containers without interpreting prompt text."""
    result = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "id" and isinstance(item, str):
                result.add(canonical_blocker_id(item))
            elif key in {"blockers", "blocker_ids", "errors"}:
                if isinstance(item, (list, tuple)):
                    result.update(canonical_blocker_id(part) for part in item if isinstance(part, str))
                result.update(_blocker_ids(item))
            elif key == "family_blockers" and isinstance(item, Mapping):
                for blockers in item.values():
                    if isinstance(blockers, (list, tuple)):
                        result.update(canonical_blocker_id(part) for part in blockers
                                      if isinstance(part, str))
            elif isinstance(item, (Mapping, list, tuple)):
                result.update(_blocker_ids(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.update(_blocker_ids(item))
    return result


def _candidate(row: Mapping[str, Any]) -> dict[str, Any] | None:
    if row.get("normal", {}).get("realizer_version") != "v1":
        return None
    signature = row.get("coverage_signature")
    if not isinstance(signature, Mapping):
        raise ValueError("ordinary fallback row is missing coverage_signature")
    if signature.get("schema_version") != "realizer-coverage-signature/v1":
        raise ValueError("unsupported coverage signature schema")
    if signature.get("proof_basis") == "invalid_common_inputs":
        return None
    if any(is_hard_excluded(identifier) for identifier in _blocker_ids(row)):
        return None
    if signature.get("proof_basis") not in {"common_reconstructed", "legacy_diagnostic"}:
        raise ValueError("unsupported coverage signature proof_basis")
    sha = row.get("coverage_signature_sha256")
    seed = row.get("run_seed")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        raise ValueError("coverage signature SHA-256 must be 64 lowercase hexadecimal characters")
    if type(seed) is not int or seed < 0:
        raise ValueError("run_seed must be a nonnegative integer")
    blocked_domains = signature.get("blocked_domains")
    family_blockers = signature.get("family_blockers")
    if (not isinstance(blocked_domains, list)
            or any(not isinstance(domain, str) for domain in blocked_domains)
            or not isinstance(family_blockers, Mapping)):
        raise ValueError("coverage signature requires blocked_domains and family_blockers")
    targets, repairable = set(), set()
    # Fresh diagnostic proof replaces ordinary route-only rejection reasons.
    # Ordinary blockers were still inspected above for hard integrity failures.
    for family, ids in family_blockers.items():
        if not isinstance(ids, list) or any(not isinstance(identifier, str) for identifier in ids):
            raise ValueError("family_blockers values must be lists of blocker IDs")
        ids = [canonical_blocker_id(identifier) for identifier in ids]
        if family not in REQUIRED_FAMILIES or ROUTE_ONLY_EXCLUDE_IDS.intersection(ids):
            continue
        if row.get("families", {}).get(family, {}).get("constructor_present") is False:
            continue
        family_repairable = {identifier for identifier in ids if is_repairable_blocker(identifier)}
        if not family_repairable or any(
            identifier not in family_repairable and identifier != "family.legacy_route_ceiling"
            for identifier in ids
        ):
            continue
        targets.add(family)
        repairable.update(family_repairable)
    if not targets:
        return None
    return {"sha": sha, "seed": seed, "blocked_domains": set(blocked_domains),
            "target_family_keys": targets, "repairable_blocker_ids": repairable}


def select_packets(rows: Sequence[Mapping[str, Any]], *, max_packets: int = 3) -> list[dict[str, Any]]:
    """Select up to three structural fallback groups without mutating input rows."""
    if type(max_packets) is not int or not 0 <= max_packets <= 3:
        raise ValueError("max_packets must be an integer between 0 and 3")
    observed = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each audit row must be an object")
        if row.get("normal", {}).get("realizer_version") == "v2":
            observed.update(family for family, result in row.get("families", {}).items()
                            if result.get("executed_v2") is True)
    groups = {}
    for row in rows:
        candidate = _candidate(row)
        if candidate is None:
            continue
        group = groups.setdefault(candidate["sha"], {
            "seed_set": set(), "blocked_domains": set(),
            "target_family_keys": set(), "repairable_blocker_ids": set(),
        })
        group["seed_set"].add(candidate["seed"])
        for field in ("blocked_domains", "target_family_keys", "repairable_blocker_ids"):
            group[field].update(candidate[field])
    ranked = []
    for sha, group in groups.items():
        count = len(group["seed_set"])
        if count < 4:
            continue
        score = (count, len(group["target_family_keys"] - observed),
                 -len(group["blocked_domains"]), -len(group["repairable_blocker_ids"]))
        ranked.append((score, sha, group))
    ranked.sort(key=lambda item: (tuple(-part for part in item[0]), item[1]))
    packets = []
    for index, (_, sha, group) in enumerate(ranked[:max_packets]):
        seeds = sorted(group["seed_set"])
        packets.append({
            "schema_version": "r44-coverage-packet/v1",
            "packet_id": f"R44-{chr(ord('A') + index)}",
            "coverage_signature_sha256": sha,
            "distinct_seed_count": len(seeds),
            "blocked_domains": sorted(group["blocked_domains"]),
            "repairable_blocker_ids": sorted(group["repairable_blocker_ids"]),
            "target_family_keys": sorted(group["target_family_keys"]),
            "seed_set": seeds,
            "example_seeds": seeds[:8],
            "projected_upper_bound": len(seeds),
            "acceptance_min_new_ordinary": max(4, min(16, len(seeds) // 2)),
        })
    return packets


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-packets", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.rows.resolve() == args.output.resolve():
            raise ValueError("input rows and output must be different files")
        rows = []
        with args.rows.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON on row {line_number}") from exc
        packets = select_packets(rows, max_packets=args.max_packets)
        serialized = json.dumps(packets, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        print(f"packet selection failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
