"""Immutable internal evidence; no family authorization or public serialization.

Bindings detect stale input and reconstructed-fact mismatches, not cryptographic
authenticity. All seven domains have adapters; unsupported grammar stays unknown.
The bounded source fingerprint describes this process's imported source snapshot,
not the audit's full repository source_tree_hash. Source changes require a fresh
process; audit runners independently check their whole source before and after.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = 'realization-evidence/v1'
DOMAINS = ('action', 'clothing', 'garnish', 'mood', 'scene', 'subject', 'template')
Domain = Literal['subject', 'clothing', 'action', 'scene', 'template', 'garnish', 'mood']
ProofMode = Literal['exact_renderer_replay', 'bound_constructor']


class Truth(Enum):
    TRUE = 'true'
    FALSE = 'false'
    UNKNOWN = 'unknown'

    def __bool__(self):
        raise TypeError('Compare Truth explicitly with Truth.TRUE/FALSE/UNKNOWN')


def truth_from_optional(value: bool | None) -> Truth:
    if value is True:
        return Truth.TRUE
    if value is False:
        return Truth.FALSE
    if value is None:
        return Truth.UNKNOWN
    raise TypeError('A legacy fact must be bool or None')


def _immutable(value):
    if value is None or type(value) in (str, bool, int) or isinstance(value, Truth):
        return
    if type(value) is tuple:
        for child in value:
            _immutable(child)
        return
    if isinstance(value, _EvidenceValue) and is_dataclass(value):
        for field in fields(value):
            _immutable(getattr(value, field.name))
        return
    raise TypeError('Evidence fields must contain immutable scalar/tuple/evidence values')


class _EvidenceValue:
    def __post_init__(self):
        for field in fields(self):
            _immutable(getattr(self, field.name))


@dataclass(frozen=True)
class SourceRef(_EvidenceValue):
    domain: Domain
    producer: str
    field: str
    catalog_key: str | None
    selected_text_sha256: str


@dataclass(frozen=True)
class ProducerPart(_EvidenceValue):
    part_id: str
    source: SourceRef
    text: str


@dataclass(frozen=True)
class ProducerTrace(_EvidenceValue):
    mode: ProofMode
    producer: str
    source_identity_sha256: str
    input_binding_sha256: str
    raw_output_sha256: str
    emitted_output_sha256: str
    parts: tuple[ProducerPart, ...]
    emitted_part_ids: tuple[str, ...]
    omitted_parts: tuple[tuple[str, str], ...] | None
    constructor_id: str


@dataclass(frozen=True)
class ClauseEvidence(_EvidenceValue):
    atom_id: str
    source_part_ids: tuple[str, ...]
    source_text: str
    grammar_known: Truth
    grammatical_subject_id: str | None
    owner_id: str | None
    form: str
    attachment: str
    same_subject: Truth
    place_refs: tuple[str, ...] | None
    antecedent_ids: tuple[str, ...] | None
    rule_ids: tuple[str, ...]
    grammatical_head: str | None = None


@dataclass(frozen=True)
class EvidenceComponent(_EvidenceValue):
    domain: Domain
    trace: ProducerTrace | None
    atoms: tuple[ClauseEvidence, ...]
    runtime_available: bool
    blockers: tuple[str, ...]
    facts: tuple[tuple[str, Truth], ...] = ()


@dataclass(frozen=True)
class RealizationEvidence(_EvidenceValue):
    schema_version: str
    source_identity_sha256: str
    input_binding_sha256: str
    components: tuple[EvidenceComponent, ...]


@dataclass(frozen=True)
class FamilyProof(_EvidenceValue):
    family: str
    input_binding_sha256: str
    plan_binding_sha256: str
    catalog_binding_sha256: str
    construction_binding_sha256: str | None
    constructor_id: str | None
    eligible: bool
    facts: tuple[tuple[str, Truth], ...]
    blocker_ids: tuple[str, ...]
    transform_rule_ids: tuple[str, ...]
    source_atom_map: tuple[tuple[str, str], ...]


def text_sha256(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError('Source text must be a string')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _json_input(value):
    """Copy JSON-compatible input without lossy string/key/type coercion."""
    if value is None or type(value) in (str, bool, int, float):
        return value
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError('Input keys must be strings')
        return {key: _json_input(child) for key, child in value.items()}
    if type(value) in (list, tuple):
        return [_json_input(child) for child in value]
    raise TypeError('Builder evidence inputs must be JSON values; serialize schema objects explicitly')


def _canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def _source_identity():
    # Fixed dependency list, evaluated once on module import. Never scan the repo
    # on a Builder call or put absolute checkout/output paths into the binding.
    root = Path(__file__).resolve().parents[1]
    names = (
        'pipeline/realization_evidence.py', 'pipeline/v2_structural_evidence.py',
        'pipeline/action_renderer.py', 'pipeline/v2_leaf_grammar.py',
        'pipeline/action_generator.py', 'pipeline/action_parser.py', 'core/schema.py',
        'pipeline/clothing_candidate_renderer.py', 'pipeline/clothing_candidate_selector.py',
        'pipeline/v2_clothing_provenance.py', 'history_service.py', 'clothing_service.py',
        'core/semantic_policy.py', 'location_service.py', 'vocab/seed_utils.py',
        'vocab/loc_tag_builder.py', 'vocab/loader.py', 'vocab/clothing/__init__.py',
        'vocab/clothing/constants.py', 'vocab/clothing/concept_packs.py', 'vocab/clothing/theme_map.py',
        'pipeline/location_builder.py', 'pipeline/location_policy.py', 'pipeline/location_segment_selector.py',
        'pipeline/location_semantics.py', 'pipeline/semantic_epig.py', 'pipeline/v2_scene_provenance.py',
        'core/solo_safety.py', 'object_focus_service.py', 'vocab/semantic_space.py',
        'vocab/background/__init__.py', 'vocab/background/concept_packs.py', 'vocab/background/defaults.py',
        'vocab/background/loc_tag_map.py',
        'pipeline/v2_template_provenance.py', 'pipeline/v2_support_provenance.py',
        'pipeline/v2_direct_provenance.py', 'pipeline/character_profile_pipeline.py',
        'character_service.py', 'scene_service.py', 'prompt_renderer.py', 'mood_map.json',
        'pipeline/family_capabilities.py', 'pipeline/prompt_realizer.py', 'pipeline/syntax_family_selector.py',
        'vocab/syntax_families.py',
        'pipeline/v2_candidate_bridge.py', 'pipeline/prompt_orchestrator.py',
        'core/semantic_families.py',
        'pipeline/v2_common_action_grammar.py',
    )
    code = tuple((name, hashlib.sha256((root / name).read_bytes()).hexdigest()) for name in names)
    if __package__ and '.' in __package__:
        from ..vocab.loader import load_json
        from ..character_service import load_character_profiles
        from ..scene_service import load_scene_compatibility
    else:
        from vocab.loader import load_json
        from character_service import load_character_profiles
        from scene_service import load_scene_compatibility
    # Hash the actual loaded catalog values, not mutable references to caches.
    # Choice/theme mapping iteration order affects clothing draws. Preserve the
    # loaded catalogs' order in this fingerprint, even though input bindings sort keys.
    catalogs = tuple((name, hashlib.sha256(json.dumps(load_json(name), ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest())
        for name in ('natural_language_realizer_v2.json', 'template_catalog.json',
                     'clothing_packs.json', 'clothing_constants.json', 'clothing_theme_map.json',
                     'policy_terms.json', 'background_packs.json', 'background_alias_overrides.json',
                     'background_loc_tag_map.json', 'loc_aliases_canonical.json',
                     'loc_aliases_legacy.json', 'loc_aliases_fallback.json', 'background_defaults.json',
                     'location_axis_profiles.json', 'staging_axis_descriptors.json', 'semantic_epig_config.json',
                     'object_concentration_policy.json', 'object_relation_profiles.json'))
    support_catalogs = (
        ('character_profiles', load_character_profiles()),
        ('scene_compatibility', load_scene_compatibility()),
    )
    return hashlib.sha256(_canonical({'scope': 'r43-producer-evidence-source/v1', 'code': code,
                                     'catalogs': catalogs, 'support_catalogs': support_catalogs})).hexdigest()


_SOURCE_IDENTITY_SHA256 = _source_identity()


def runtime_source_identity() -> str:
    return _SOURCE_IDENTITY_SHA256


def build_realization_evidence(builder_inputs: Mapping, *, producer_context=None) -> RealizationEvidence:
    """Bind semantic inputs and adapt all seven domains without family permission.

    Callers provide received/current semantic values, including selected template
    entries and palette when available. Missing action/frame are not reconstructed
    from audit-only node settings or a guessed default. Additional input fields
    participate in binding but cannot independently authorize any producer/family.
    """
    if not isinstance(builder_inputs, Mapping):
        raise TypeError('builder_inputs must be a mapping')
    inputs = _json_input(builder_inputs)
    producer = _json_input(producer_context)
    binding = hashlib.sha256(_canonical({'schema_version': SCHEMA_VERSION,
        'source_identity_sha256': runtime_source_identity(), 'builder_inputs': inputs,
        'producer_context': producer})).hexdigest()
    from .v2_structural_evidence import adapt_action_component
    from .v2_clothing_provenance import adapt_clothing_component
    from .v2_scene_provenance import adapt_scene_component
    from .v2_template_provenance import adapt_template_component
    from .v2_support_provenance import adapt_subject_component, adapt_garnish_component, adapt_mood_component
    action = adapt_action_component(inputs.get('action_frame'), inputs.get('action'),
        input_binding_sha256=binding, source_identity_sha256=runtime_source_identity(),
        context=inputs.get('context'))
    if 'clothing' in inputs and not isinstance(inputs['clothing'], str):
        clothing = EvidenceComponent('clothing', None, (), False, ('binding.current_text_mismatch',))
    else:
        clothing = adapt_clothing_component(inputs.get('context'), inputs.get('clothing'),
            input_binding_sha256=binding, source_identity_sha256=runtime_source_identity())
    if 'scene' in inputs and not isinstance(inputs['scene'], str):
        scene = EvidenceComponent('scene', None, (), False, ('binding.current_text_mismatch',))
    else:
        scene = adapt_scene_component(inputs.get('context'), inputs.get('scene'), inputs.get('action_frame'),
            input_binding_sha256=binding, source_identity_sha256=runtime_source_identity())
    adapted = {'action': action, 'clothing': clothing, 'scene': scene}
    for domain, adapter in (
        ('template', adapt_template_component), ('subject', adapt_subject_component),
        ('garnish', adapt_garnish_component), ('mood', adapt_mood_component),
    ):
        adapted[domain] = adapter(inputs, input_binding_sha256=binding,
                                  source_identity_sha256=runtime_source_identity())
    components = tuple(adapted[domain] for domain in DOMAINS)
    return RealizationEvidence(SCHEMA_VERSION, runtime_source_identity(), binding, components)


def evidence_to_dict(evidence: RealizationEvidence) -> dict:
    """Explicit external-receipt projection, never part of PromptContext.to_dict."""
    if type(evidence) is not RealizationEvidence:
        raise TypeError('Expected this module\'s RealizationEvidence')
    _immutable(evidence)
    def project(value):
        if isinstance(value, Truth):
            return value.value
        if isinstance(value, _EvidenceValue):
            return {field.name: project(getattr(value, field.name)) for field in fields(value)}
        if isinstance(value, tuple):
            return [project(child) for child in value]
        return value
    return project(evidence)


def evidence_bytes(evidence: RealizationEvidence) -> bytes:
    return _canonical(evidence_to_dict(evidence))


def validate_evidence_binding(evidence, builder_inputs, *, producer_context=None) -> bool:
    """Rebuild current facts; a matching caller-supplied digest is insufficient."""
    if type(evidence) is not RealizationEvidence or evidence.schema_version != SCHEMA_VERSION:
        return False
    try:
        expected = build_realization_evidence(builder_inputs, producer_context=producer_context)
        # Dataclass equality distinguishes Enum/string, while canonical bytes
        # distinguish values such as True/1 that Python equality otherwise merges.
        return evidence == expected and evidence_bytes(evidence) == evidence_bytes(expected)
    except (TypeError, ValueError, AttributeError, KeyError):
        return False
