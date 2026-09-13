"""Diagnostic-only typed capability identities projected from current evidence."""
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from pipeline.realization_evidence import Truth, build_realization_evidence
from tools.workflow_prompt_runner import canonical_json_bytes

SCHEMA_VERSION = 'realizer-capability-projection/v1'


def capability_sha256(identity: Mapping) -> str:
    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def _owner_class(atom) -> str:
    subject, owner = atom.grammatical_subject_id, atom.owner_id
    if isinstance(subject, str) and subject.startswith('body:') and owner == 'protagonist':
        return 'protagonist_body_part'
    if any(isinstance(value, str) and value.startswith('object:') for value in (subject, owner)):
        return 'primary_object_part'
    if any(isinstance(value, str) and value.startswith('event:') for value in (subject, owner)):
        return 'scene_event'
    if subject == 'protagonist' or owner == 'protagonist':
        return 'protagonist'
    return 'unknown'


def _catalog_source_class(domain: str, source) -> str:
    if domain == 'clothing' and source.field.startswith('character_palette.'):
        return 'character_palette'
    if source.catalog_key is None:
        return 'producer'
    if domain == 'scene':
        return 'background_defaults' if source.catalog_key == 'background_defaults' else 'location_pack'
    return {
        'clothing': 'selected_clothing_pack',
        'subject': 'character_profile',
        'template': 'template_catalog',
        'mood': 'mood_catalog',
    }.get(domain, 'catalog')


def _constructor_class(value: str) -> str:
    if not isinstance(value, str) or not value:
        return 'unknown'
    if value.startswith('action_slots:'):
        return 'action_slots'
    return value.removesuffix('/v1')


def project_evidence_capabilities(evidence) -> list[dict]:
    """Project domain-local atoms while preserving their typed part relation."""
    projected = []
    for component in evidence.components:
        if component.trace is None:
            continue
        parts = {part.part_id: part for part in component.trace.parts}
        for atom in component.atoms:
            try:
                sources = [parts[part_id].source for part_id in atom.source_part_ids]
            except KeyError as exc:
                raise ValueError('capability atom references an unknown producer part') from exc
            identity = {
                'schema_version': SCHEMA_VERSION,
                'domain': component.domain,
                'capability_kind': 'clause_atom',
                'producer_class': component.trace.producer,
                'constructor_class': _constructor_class(component.trace.constructor_id),
                'source_field_classes': [source.field for source in sources],
                'catalog_source_classes': [
                    _catalog_source_class(component.domain, source) for source in sources
                ],
                'form_class': atom.form if isinstance(atom.form, str) and atom.form else 'unknown',
                'attachment_class': (
                    atom.attachment if isinstance(atom.attachment, str) and atom.attachment else 'unknown'
                ),
                'owner_class': _owner_class(atom),
                'grammar_state': (
                    atom.grammar_known.value if isinstance(atom.grammar_known, Truth) else 'unknown'
                ),
                'source_bound': True,
            }
            projected.append({
                'capability': identity,
                'capability_sha256': capability_sha256(identity),
            })
    return sorted(
        projected,
        key=lambda item: (item['capability']['domain'], item['capability_sha256']),
    )


def build_capability_projection(snapshot: Mapping, coverage_signature: Mapping) -> dict:
    """Rebuild current evidence only when R44 validated common inputs."""
    unavailable = {
        'schema_version': SCHEMA_VERSION,
        'status': 'NOT_AVAILABLE',
        'capabilities': [],
    }
    if coverage_signature.get('proof_basis') != 'common_reconstructed':
        return unavailable
    bridge = snapshot.get('bridge')
    if not isinstance(bridge, Mapping) or 'common_inputs' not in bridge:
        raise ValueError('common reconstructed projection is missing current inputs')
    evidence = build_realization_evidence(bridge['common_inputs'])
    return {
        'schema_version': SCHEMA_VERSION,
        'status': 'AVAILABLE',
        'capabilities': project_evidence_capabilities(evidence),
    }
