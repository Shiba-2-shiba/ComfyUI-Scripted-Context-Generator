from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


RUNTIME_PATH = ROOT / "vocab" / "data" / "action_pools.json"
SOURCE_DIR = ROOT / "vocab" / "source" / "action_pools"
MANIFEST_PATH = SOURCE_DIR / "_manifest.json"
SHARED_FAMILIES_PATH = SOURCE_DIR / "_shared_families.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, ensure_ascii=False, indent=indent) + "\n").encode("utf-8"))


def _is_location_pool(key: str, value: Any) -> bool:
    return key != "schema_version" and not key.startswith("_") and isinstance(value, list)


def read_runtime_action_pools(path: Path = RUNTIME_PATH) -> Dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def runtime_location_order(payload: Dict[str, Any]) -> List[str]:
    return [key for key, value in payload.items() if _is_location_pool(str(key), value)]


def source_path_for_location(location: str) -> Path:
    return SOURCE_DIR / f"{location}.json"


def shared_families_path() -> Path:
    return SHARED_FAMILIES_PATH


def build_source_manifest(runtime_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "runtime_comment": str(runtime_payload.get("_comment", "")),
        "runtime_schema_version": str(runtime_payload.get("schema_version", "")),
        "location_order": runtime_location_order(runtime_payload),
    }


def build_source_payload(location: str, actions: Sequence[Any]) -> Dict[str, Any]:
    return {
        "location": location,
        "actions": list(actions),
    }


def write_source_files(runtime_path: Path = RUNTIME_PATH) -> Dict[str, Any]:
    runtime_payload = read_runtime_action_pools(runtime_path)
    manifest = build_source_manifest(runtime_payload)
    _write_json(MANIFEST_PATH, manifest)
    for location in manifest["location_order"]:
        _write_json(source_path_for_location(location), build_source_payload(location, runtime_payload[location]))
    return {
        "source_dir": str(SOURCE_DIR.relative_to(ROOT)),
        "location_file_count": len(manifest["location_order"]),
    }


def _empty_report() -> Dict[str, List[dict]]:
    return {"ERROR": [], "WARNING": [], "INFO": []}


def read_shared_families(report: Dict[str, List[dict]] | None = None) -> Dict[str, List[Any]]:
    report = report if report is not None else _empty_report()
    if not SHARED_FAMILIES_PATH.exists():
        return {}

    payload = _read_json(SHARED_FAMILIES_PATH)
    if not isinstance(payload, dict):
        report["ERROR"].append({"code": "shared_action_families_invalid"})
        return {}
    if payload.get("schema_version") != "1.0":
        report["ERROR"].append({"code": "unsupported_shared_action_family_schema", "value": payload.get("schema_version")})

    families = payload.get("families", {})
    if not isinstance(families, dict):
        report["ERROR"].append({"code": "shared_action_families_missing"})
        return {}

    normalized: Dict[str, List[Any]] = {}
    for family_name, actions in families.items():
        if not isinstance(family_name, str) or not family_name:
            report["ERROR"].append({"code": "shared_action_family_name_invalid", "family": family_name})
            continue
        if not isinstance(actions, list) or not actions:
            report["ERROR"].append({"code": "shared_action_family_actions_invalid", "family": family_name})
            continue
        normalized[family_name] = actions
    return normalized


def _action_text(action: Any) -> str:
    if isinstance(action, dict):
        return str(action.get("text", "")).strip()
    return str(action).strip()


def _expand_family_ref(
    location: str,
    family_ref: Any,
    shared_families: Dict[str, List[Any]],
    report: Dict[str, List[dict]],
) -> List[Any]:
    if isinstance(family_ref, str):
        family_name = family_ref
        take = None
        offset = 0
    elif isinstance(family_ref, dict):
        family_name = str(family_ref.get("name") or family_ref.get("family") or "")
        take = family_ref.get("take")
        offset = int(family_ref.get("offset", 0) or 0)
    else:
        report["ERROR"].append({"code": "action_pool_family_ref_invalid", "location": location, "family_ref": family_ref})
        return []

    if family_name not in shared_families:
        report["ERROR"].append({"code": "action_pool_family_missing", "location": location, "family": family_name})
        return []
    if offset < 0:
        report["ERROR"].append({"code": "action_pool_family_offset_invalid", "location": location, "family": family_name, "offset": offset})
        return []
    if take is None:
        take_count = len(shared_families[family_name]) - offset
    else:
        take_count = int(take)
    if take_count < 0:
        report["ERROR"].append({"code": "action_pool_family_take_invalid", "location": location, "family": family_name, "take": take})
        return []
    return list(shared_families[family_name][offset : offset + take_count])


def expand_source_payload(
    location: str,
    payload: Dict[str, Any],
    shared_families: Dict[str, List[Any]],
    report: Dict[str, List[dict]],
) -> List[Any]:
    actions = payload.get("actions")
    if not isinstance(actions, list):
        report["ERROR"].append({"code": "action_pool_source_actions_invalid", "location": location})
        return []

    expanded = list(actions)
    family_refs = payload.get("families", [])
    if family_refs:
        if not isinstance(family_refs, list):
            report["ERROR"].append({"code": "action_pool_source_families_invalid", "location": location})
            return expanded
        for family_ref in family_refs:
            expanded.extend(_expand_family_ref(location, family_ref, shared_families, report))

    duplicates = sorted({text for text in (_action_text(action) for action in expanded) if text and sum(1 for item in expanded if _action_text(item) == text) > 1})
    if duplicates:
        report["ERROR"].append({"code": "action_pool_source_duplicate_actions", "location": location, "actions": duplicates[:12]})
    return expanded


def read_source_action_pools(report: Dict[str, List[dict]] | None = None) -> Dict[str, Any]:
    report = report if report is not None else _empty_report()
    if not MANIFEST_PATH.exists():
        report["ERROR"].append({"code": "action_pool_manifest_missing", "path": str(MANIFEST_PATH.relative_to(ROOT))})
        return {}

    manifest = _read_json(MANIFEST_PATH)
    if not isinstance(manifest, dict):
        report["ERROR"].append({"code": "action_pool_manifest_invalid"})
        return {}

    if manifest.get("schema_version") != "1.0":
        report["ERROR"].append({"code": "unsupported_action_pool_source_schema", "value": manifest.get("schema_version")})

    locations = manifest.get("location_order", [])
    if not isinstance(locations, list) or not all(isinstance(item, str) and item for item in locations):
        report["ERROR"].append({"code": "action_pool_manifest_location_order_invalid"})
        return {}

    duplicates = sorted({location for location in locations if locations.count(location) > 1})
    if duplicates:
        report["ERROR"].append({"code": "duplicate_action_pool_source_locations", "locations": duplicates})

    shared_families = read_shared_families(report)

    generated: Dict[str, Any] = {
        "_comment": str(manifest.get("runtime_comment", "")),
        "schema_version": str(manifest.get("runtime_schema_version", "")),
    }
    for location in locations:
        path = source_path_for_location(location)
        if not path.exists():
            report["ERROR"].append({"code": "action_pool_source_missing", "location": location, "path": str(path.relative_to(ROOT))})
            continue
        payload = _read_json(path)
        if not isinstance(payload, dict):
            report["ERROR"].append({"code": "action_pool_source_invalid", "location": location})
            continue
        if payload.get("location") != location:
            report["ERROR"].append(
                {
                    "code": "action_pool_source_location_mismatch",
                    "expected": location,
                    "actual": payload.get("location"),
                    "path": str(path.relative_to(ROOT)),
                }
            )
        generated[location] = expand_source_payload(location, payload, shared_families, report)

    manifest_names = {f"{location}.json" for location in locations}
    existing_names = {
        path.name
        for path in SOURCE_DIR.glob("*.json")
        if path.name not in {"_manifest.json", "_shared_families.json"}
    }
    extra_files = sorted(existing_names - manifest_names)
    if extra_files:
        report["ERROR"].append({"code": "action_pool_source_orphan_files", "files": extra_files})

    return generated


def _location_sample(payload: Dict[str, Any], limit: int = 12) -> List[str]:
    return runtime_location_order(payload)[:limit]


def build_check_report() -> Dict[str, List[dict]]:
    report = _empty_report()
    runtime_payload = read_runtime_action_pools()
    generated_payload = read_source_action_pools(report)

    if generated_payload and generated_payload != runtime_payload:
        runtime_keys = set(runtime_location_order(runtime_payload))
        generated_keys = set(runtime_location_order(generated_payload))
        changed_locations = sorted(
            key
            for key in runtime_keys & generated_keys
            if runtime_payload.get(key) != generated_payload.get(key)
        )
        report["ERROR"].append(
            {
                "code": "action_pools_generated_drift",
                "missing_source_locations": sorted(runtime_keys - generated_keys),
                "extra_source_locations": sorted(generated_keys - runtime_keys),
                "changed_location_sample": changed_locations[:12],
            }
        )

    report["INFO"].append(
        {
            "code": "action_pool_source_summary",
            "runtime_location_count": len(runtime_location_order(runtime_payload)),
            "source_location_count": len(runtime_location_order(generated_payload)) if generated_payload else 0,
            "runtime_location_sample": _location_sample(runtime_payload),
        }
    )
    return report


def write_runtime_from_source(output_path: Path = RUNTIME_PATH) -> None:
    report = _empty_report()
    payload = read_source_action_pools(report)
    if report["ERROR"]:
        raise ValueError(json.dumps(report, ensure_ascii=False))
    _write_json(output_path, payload, indent=4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check action_pools.json from split source files.")
    parser.add_argument("--check", action="store_true", help="Compare source files with vocab/data/action_pools.json.")
    parser.add_argument("--write-source", action="store_true", help="Create split source files from current runtime JSON.")
    parser.add_argument("--write", action="store_true", help="Write runtime action_pools.json from split source files.")
    parser.add_argument("--output", default=str(RUNTIME_PATH), help="Output path for --write.")
    args = parser.parse_args()

    if args.write_source:
        print(json.dumps({"INFO": [write_source_files()]}, ensure_ascii=False, indent=2))
        return 0

    report = build_check_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.write:
        source_report = _empty_report()
        read_source_action_pools(source_report)
        if source_report["ERROR"]:
            print(json.dumps(source_report, ensure_ascii=False, indent=2))
            return 1
        write_runtime_from_source(Path(args.output))
        return 0

    return 1 if report["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
