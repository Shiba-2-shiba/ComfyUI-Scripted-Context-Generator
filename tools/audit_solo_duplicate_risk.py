from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.solo_safety import is_solo_action_safe_text, solo_duplicate_risk_flags


ACTION_POOLS_PATH = ROOT / "vocab" / "data" / "action_pools.json"
FIXTURE_PATH = ROOT / "assets" / "fixtures" / "solo_duplicate_prompt_cases.json"
MOOD_MAP_PATH = ROOT / "mood_map.json"
PERSONALITY_PROFILES_PATH = ROOT / "vocab" / "data" / "personality_behavior_profiles.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _risk_item(source: str, key: str, text: str, *, action_candidate: bool = False) -> dict | None:
    flags = sorted(solo_duplicate_risk_flags(text))
    action_safe = is_solo_action_safe_text(text) if action_candidate else None
    if not flags and action_safe is not False:
        return None
    item = {"source": source, "key": key, "text": text, "risk_families": flags}
    if action_safe is not None:
        item["solo_action_safe"] = action_safe
    return item


def _audit_action_pools() -> List[dict]:
    data = _load_json(ACTION_POOLS_PATH)
    findings: List[dict] = []
    for location, actions in data.items():
        if not isinstance(actions, list):
            continue
        for index, action in enumerate(actions):
            text = str(action.get("text", "") if isinstance(action, dict) else action).strip()
            item = _risk_item("action_pools", f"{location}[{index}]", text, action_candidate=True)
            if item:
                findings.append(item)
    return findings


def _audit_fixture_prompts() -> List[dict]:
    if not FIXTURE_PATH.exists():
        return []
    findings: List[dict] = []
    for case in _load_json(FIXTURE_PATH):
        item = _risk_item("solo_duplicate_prompt_cases", str(case.get("name", "")), str(case.get("prompt", "")))
        if item:
            findings.append(item)
    return findings


def _audit_mood_map() -> List[dict]:
    data = _load_json(MOOD_MAP_PATH)
    findings: List[dict] = []
    for mood_key, mood_data in data.items():
        if not isinstance(mood_data, dict):
            continue
        for field in ("description", "staging_tags"):
            for index, text in enumerate(mood_data.get(field, []) or []):
                item = _risk_item("mood_map", f"{mood_key}.{field}[{index}]", str(text), action_candidate=True)
                if item:
                    findings.append(item)
    return findings


def _audit_personality_profiles() -> List[dict]:
    data = _load_json(PERSONALITY_PROFILES_PATH)
    findings: List[dict] = []
    for profile_key, profile_data in data.items():
        if not isinstance(profile_data, dict):
            continue
        for field, values in profile_data.items():
            if not isinstance(values, list):
                continue
            for index, entry in enumerate(values):
                text = str(entry.get("text", "") if isinstance(entry, dict) else entry).strip()
                item = _risk_item("personality_behavior_profiles", f"{profile_key}.{field}[{index}]", text, action_candidate=True)
                if item:
                    findings.append(item)
    return findings


def build_report() -> Dict[str, List[dict]]:
    findings = []
    findings.extend(_audit_fixture_prompts())
    findings.extend(_audit_action_pools())
    findings.extend(_audit_mood_map())
    findings.extend(_audit_personality_profiles())
    return {
        "ERROR": [],
        "WARNING": findings,
        "INFO": [
            {
                "code": "solo_duplicate_risk_summary",
                "finding_count": len(findings),
                "unsafe_action_candidate_count": sum(1 for item in findings if item.get("solo_action_safe") is False),
            }
        ],
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
