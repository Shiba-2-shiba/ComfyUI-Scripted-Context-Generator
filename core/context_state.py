from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .context_ops import ensure_context


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce_palette_list(value: Any, fallback_text: str = "") -> list[str]:
    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        if normalized:
            return normalized
    text = _coerce_text(fallback_text).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


@dataclass
class CharacterState:
    character_name: str = ""
    character_id: str = ""
    personality: str = ""
    palette: list[str] = field(default_factory=list)
    palette_text: str = ""
    source_subj_key: str = ""


@dataclass
class ClothingState:
    raw_costume_key: str = ""
    resolved_theme: str = ""
    clothing_prompt: str = ""


@dataclass
class LocationState:
    raw_loc_tag: str = ""
    resolved_location_key: str = ""
    location_prompt: str = ""


@dataclass
class PromptFragments:
    garnish: str = ""
    staging_tags: str = ""


@dataclass
class GenerationState:
    character: CharacterState = field(default_factory=CharacterState)
    clothing: ClothingState = field(default_factory=ClothingState)
    location: LocationState = field(default_factory=LocationState)
    fragments: PromptFragments = field(default_factory=PromptFragments)

    @classmethod
    def from_context(cls, context: Any) -> "GenerationState":
        ctx = ensure_context(context)
        extras = ctx.extras if isinstance(ctx.extras, dict) else {}

        palette_text = _coerce_text(extras.get("character_palette_str", "")).strip()
        palette = _coerce_palette_list(extras.get("color_palette", []), fallback_text=palette_text)
        if not palette_text and palette:
            palette_text = ", ".join(palette)

        return cls(
            character=CharacterState(
                character_name=_coerce_text(extras.get("character_name", "")).strip(),
                character_id=_coerce_text(extras.get("character_id", "")).strip(),
                personality=_coerce_text(extras.get("personality", "")).strip(),
                palette=palette,
                palette_text=palette_text,
                source_subj_key=_coerce_text(extras.get("source_subj_key", "")).strip() or _coerce_text(ctx.subj).strip(),
            ),
            clothing=ClothingState(
                raw_costume_key=_coerce_text(extras.get("raw_costume_key", "")).strip() or _coerce_text(ctx.costume).strip(),
                resolved_theme=_coerce_text(ctx.costume).strip(),
                clothing_prompt=_coerce_text(extras.get("clothing_prompt", "")).strip(),
            ),
            location=LocationState(
                raw_loc_tag=_coerce_text(extras.get("raw_loc_tag", "")).strip() or _coerce_text(ctx.loc).strip(),
                resolved_location_key=_coerce_text(ctx.loc).strip(),
                location_prompt=_coerce_text(extras.get("location_prompt", "")).strip(),
            ),
            fragments=PromptFragments(
                garnish=_coerce_text(extras.get("garnish", "")).strip(),
                staging_tags=_coerce_text(extras.get("staging_tags", "")).strip(),
            ),
        )

    def to_extras_patch(self) -> Dict[str, Any]:
        return {
            "character_name": self.character.character_name,
            "character_id": self.character.character_id,
            "personality": self.character.personality,
            "color_palette": list(self.character.palette),
            "character_palette_str": self.character.palette_text,
            "source_subj_key": self.character.source_subj_key,
            "raw_costume_key": self.clothing.raw_costume_key,
            "clothing_prompt": self.clothing.clothing_prompt,
            "raw_loc_tag": self.location.raw_loc_tag,
            "location_prompt": self.location.location_prompt,
            "garnish": self.fragments.garnish,
            "staging_tags": self.fragments.staging_tags,
        }


def generation_state_from_context(context: Any) -> GenerationState:
    return GenerationState.from_context(context)
