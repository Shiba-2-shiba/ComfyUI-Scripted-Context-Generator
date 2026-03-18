from dataclasses import asdict, dataclass, field
from typing import Any, Dict
import json


CONTEXT_VERSION = "2.0"


def default_extras() -> Dict[str, Any]:
    return {
        "character_name": "",
        "hair_color": "",
        "eye_color": "",
        "personality": "",
        "color_palette": [],
        "character_palette_str": "",
        "clothing_prompt": "",
        "location_prompt": "",
        "garnish": "",
        "staging_tags": "",
        "raw_costume_key": "",
        "raw_loc_tag": "",
    }


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


@dataclass
class MetaInfo:
    """Metadata for the prompt context, affecting style and mood."""

    mood: str = ""
    style: str = ""
    tags: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetaInfo":
        if not isinstance(data, dict):
            data = {}
        tags = data.get("tags", {})
        if not isinstance(tags, dict):
            tags = {}
        return cls(
            mood=_coerce_text(data.get("mood", ""), ""),
            style=_coerce_text(data.get("style", ""), ""),
            tags=tags,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DebugInfo:
    """Diagnostic information for tracing generation decisions."""

    node: str
    seed: int
    decision: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugInfo":
        if not isinstance(data, dict):
            data = {}
        decision = data.get("decision", {})
        if not isinstance(decision, dict):
            decision = {}
        try:
            seed = int(data.get("seed", 0))
        except Exception:
            seed = 0
        return cls(
            node=_coerce_text(data.get("node", "unknown"), "unknown"),
            seed=seed,
            decision=decision,
            warnings=_coerce_str_list(data.get("warnings", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PromptContext:
    """Core context object to be passed between nodes."""

    context_version: str = CONTEXT_VERSION
    seed: int = 0
    subj: str = ""
    costume: str = ""
    loc: str = ""
    action: str = ""
    meta: MetaInfo = field(default_factory=MetaInfo)
    extras: Dict[str, Any] = field(default_factory=default_extras)
    history: list[DebugInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> "PromptContext":
        """
        Create PromptContext from dictionary.

        Args:
            data: Input dictionary.
            strict: Reserved for future validation behavior.
        """
        if not isinstance(data, dict):
            data = {}

        meta_data = data.get("meta", {})
        if not isinstance(meta_data, dict):
            meta_data = {}

        extras = default_extras()
        raw_extras = data.get("extras", {})
        if isinstance(raw_extras, dict):
            extras.update(raw_extras)

        history: list[DebugInfo] = []
        history_data = data.get("history", [])
        if isinstance(history_data, list):
            for entry in history_data:
                if isinstance(entry, dict):
                    history.append(DebugInfo.from_dict(entry))

        try:
            seed = int(data.get("seed", 0))
        except Exception:
            seed = 0

        ctx = cls(
            context_version=_coerce_text(data.get("context_version", CONTEXT_VERSION), CONTEXT_VERSION),
            seed=seed,
            subj=_coerce_text(data.get("subj", ""), ""),
            costume=_coerce_text(data.get("costume", ""), ""),
            loc=_coerce_text(data.get("loc", ""), ""),
            action=_coerce_text(data.get("action", ""), ""),
            meta=MetaInfo.from_dict(meta_data),
            extras=extras,
            history=history,
            warnings=_coerce_str_list(data.get("warnings", [])),
        )

        if strict:
            # Placeholder hook for future schema validation.
            pass

        return ctx

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "PromptContext":
        """Parse from JSON string."""
        if not json_str or json_str.strip() == "":
            return cls()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return cls(warnings=["Invalid context JSON; falling back to empty context"])
        return cls.from_dict(data)
