from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping
import json


CONTEXT_VERSION = "2.0"
LEGACY_STYLE_NOTE = "meta.style is legacy read-only compatibility metadata and ignored by prompt generation"
LEGACY_STYLE_WARNING = LEGACY_STYLE_NOTE


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
        "source_subj_key": "",
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
    """Metadata for prompt context. `style` is legacy compatibility only."""

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
class ActionFrame:
    """Typed view of the existing action-slot contract.

    ``legacy_slots`` remains the lossless compatibility projection.  The named
    fields make the roles consumed by the natural renderer explicit without
    creating a second action-generation model.
    """

    schema_version: str = "action-frame/v1"
    legacy_text: str = ""
    main_verb: str = ""
    primary_object: str = ""
    posture: str = ""
    hand_action: str = ""
    gaze_target: str = ""
    progress: str = ""
    stimulus_or_obstacle: str = ""
    social_relation: str = ""
    legacy_slots: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_slots(
        cls,
        slots: Mapping[str, Any] | None,
        *,
        legacy_text: str = "",
        main_verb: str = "",
        primary_object: str = "",
    ) -> "ActionFrame":
        normalized_slots = dict(slots) if isinstance(slots, Mapping) else {}
        return cls(
            legacy_text=_coerce_text(legacy_text),
            main_verb=_coerce_text(main_verb),
            primary_object=_coerce_text(primary_object),
            posture=_coerce_text(normalized_slots.get("posture", "")),
            hand_action=_coerce_text(normalized_slots.get("hand_action", "")),
            gaze_target=_coerce_text(normalized_slots.get("gaze_target", "")),
            progress=_coerce_text(
                normalized_slots.get("progress_state", normalized_slots.get("progress_clause", ""))
            ),
            stimulus_or_obstacle=_coerce_text(
                normalized_slots.get("obstacle_or_trigger", normalized_slots.get("obstacle_clause", ""))
            ),
            social_relation=_coerce_text(
                normalized_slots.get("social_distance", normalized_slots.get("social_clause", ""))
            ),
            legacy_slots=normalized_slots,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "ActionFrame":
        if not isinstance(data, Mapping):
            return cls()
        if data.get("schema_version", "action-frame/v1") != "action-frame/v1":
            return cls()
        slots = data.get("legacy_slots", {})
        return cls(
            schema_version="action-frame/v1",
            legacy_text=_coerce_text(data.get("legacy_text", "")),
            main_verb=_coerce_text(data.get("main_verb", "")),
            primary_object=_coerce_text(data.get("primary_object", "")),
            posture=_coerce_text(data.get("posture", "")),
            hand_action=_coerce_text(data.get("hand_action", "")),
            gaze_target=_coerce_text(data.get("gaze_target", "")),
            progress=_coerce_text(data.get("progress", "")),
            stimulus_or_obstacle=_coerce_text(data.get("stimulus_or_obstacle", "")),
            social_relation=_coerce_text(data.get("social_relation", "")),
            legacy_slots=dict(slots) if isinstance(slots, Mapping) else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_slot_dict(self) -> Dict[str, Any]:
        return dict(self.legacy_slots)

    def has_content(self) -> bool:
        return bool(
            self.legacy_text
            or self.main_verb
            or self.primary_object
            or self.legacy_slots
        )


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
    notes: list[str] = field(default_factory=list)
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
            notes=_coerce_str_list(data.get("notes", [])),
            warnings=_coerce_str_list(data.get("warnings", [])),
        )

        if ctx.meta.style and LEGACY_STYLE_NOTE not in ctx.notes:
            ctx.notes.append(LEGACY_STYLE_NOTE)

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
