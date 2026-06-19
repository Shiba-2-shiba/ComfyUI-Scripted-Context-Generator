from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping

from .prompt_risk_policy import classify_risk_families
from .semantic_families import semantic_families_for_text


COMPONENT_NAMES = (
    "subject",
    "character_profile",
    "clothing",
    "foreground_action",
    "object_relation",
    "location_core",
    "background_context",
    "props",
    "mood",
    "garnish",
)
COMPONENT_NAME_SET = set(COMPONENT_NAMES)
LAYOUT_FIRST_ORDER = (
    "subject",
    "location_core",
    "foreground_action",
    "clothing",
    "object_relation",
    "props",
    "mood",
    "garnish",
    "background_context",
)
OPTIONAL_BRANCH_COMPONENTS = {
    "background_context",
    "props",
    "garnish",
    "foreground_action",
}


@dataclass(frozen=True)
class PromptComponent:
    name: str
    text: str
    source: str
    entities: tuple[str, ...] = field(default_factory=tuple)
    families: tuple[str, ...] = field(default_factory=tuple)
    risk_families: tuple[str, ...] = field(default_factory=tuple)
    budget_cost: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


PromptIR = dict[str, list[PromptComponent]]


def normalize_component_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().strip(",.;:"))


def _infer_entities(text: str) -> tuple[str, ...]:
    parts = []
    for raw in re.split(r",|\band\b|\bwith\b|\bin\b|\bon\b|\bnear\b", str(text or ""), flags=re.IGNORECASE):
        cleaned = normalize_component_text(raw)
        if len(cleaned) >= 3:
            parts.append(cleaned)
    return tuple(dict.fromkeys(parts))


def make_prompt_component(
    name: str,
    text: str,
    *,
    source: str,
    entities: Iterable[str] | None = None,
    families: Iterable[str] | None = None,
    risk_families: Iterable[str] | None = None,
    budget_cost: int = 1,
) -> PromptComponent:
    component_name = str(name or "").strip()
    if component_name not in COMPONENT_NAME_SET:
        raise ValueError(f"unknown prompt component name: {component_name!r}")
    component_text = normalize_component_text(text)
    if not component_text:
        raise ValueError("prompt component text must be non-empty")
    inferred_families = families if families is not None else semantic_families_for_text(component_text)
    inferred_risks = risk_families if risk_families is not None else classify_risk_families(component_text)
    try:
        cost = int(budget_cost)
    except Exception:
        cost = 1
    return PromptComponent(
        name=component_name,
        text=component_text,
        source=str(source or "unknown"),
        entities=tuple(str(item).strip() for item in (entities or _infer_entities(component_text)) if str(item).strip()),
        families=tuple(sorted({str(item).strip() for item in inferred_families if str(item).strip()})),
        risk_families=tuple(sorted({str(item).strip() for item in inferred_risks if str(item).strip()})),
        budget_cost=max(1, cost),
    )


def empty_prompt_ir() -> PromptIR:
    return {name: [] for name in COMPONENT_NAMES}


def add_prompt_component(prompt_ir: PromptIR, component: PromptComponent) -> PromptIR:
    if component.name not in COMPONENT_NAME_SET:
        raise ValueError(f"unknown prompt component name: {component.name!r}")
    prompt_ir.setdefault(component.name, []).append(component)
    return prompt_ir


def build_prompt_ir(fragments: Mapping[str, object], *, source: str = "prompt_renderer") -> PromptIR:
    prompt_ir = empty_prompt_ir()
    for name in COMPONENT_NAMES:
        raw_value = fragments.get(name, "")
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        for value in values:
            text = normalize_component_text(str(value or ""))
            if not text:
                continue
            add_prompt_component(prompt_ir, make_prompt_component(name, text, source=source))
    return prompt_ir


def prompt_ir_to_dict(prompt_ir: PromptIR) -> dict[str, list[dict]]:
    return {
        name: [component.to_dict() for component in prompt_ir.get(name, [])]
        for name in COMPONENT_NAMES
    }


def prompt_ir_summary(prompt_ir: PromptIR) -> dict:
    component_counts = {name: len(prompt_ir.get(name, [])) for name in COMPONENT_NAMES}
    risks = sorted(
        {
            risk
            for components in prompt_ir.values()
            for component in components
            for risk in component.risk_families
        }
    )
    families = sorted(
        {
            family
            for components in prompt_ir.values()
            for component in components
            for family in component.families
        }
    )
    return {
        "component_names": list(COMPONENT_NAMES),
        "component_counts": component_counts,
        "present_components": [name for name in COMPONENT_NAMES if component_counts[name] > 0],
        "risk_families": risks,
        "semantic_families": families,
    }


def render_layout_first_prompt_ir(prompt_ir: PromptIR) -> str:
    clauses: list[str] = []
    for name in LAYOUT_FIRST_ORDER:
        for component in prompt_ir.get(name, []):
            text = normalize_component_text(component.text)
            if not text:
                continue
            if name == "location_core" and not text.lower().startswith(("in ", "at ", "inside ", "against ")):
                text = f"in {text}"
            clauses.append(text)
    return ", ".join(dict.fromkeys(clauses)).strip()
