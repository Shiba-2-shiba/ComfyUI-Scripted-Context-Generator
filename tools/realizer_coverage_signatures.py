"""Diagnostic structural groups; never an input to runtime authorization."""
from collections.abc import Mapping
import hashlib

from pipeline.family_capabilities import prove_all_families
from pipeline.prompt_realizer import ContentPlan
from pipeline.realization_evidence import build_realization_evidence
from tools.workflow_prompt_runner import canonical_json_bytes


SCHEMA_VERSION = 'realizer-coverage-signature/v1'
REPAIRABLE_OWNER_CLASSES = (
    'protagonist', 'protagonist_body_part', 'primary_object_part', 'scene_event', 'unknown',
)
_CURRENT_FIELDS = {'subject': '{subj}', 'clothing': '{costume}', 'scene': '{loc}',
                   'action': '{action}', 'garnish': '{garnish}', 'mood': '{meta_mood}'}


def _current_inputs(snapshot, bridge, inputs):
    """Compare JSON types too: Python's True == 1 is not source identity."""
    if not isinstance(inputs, Mapping) or inputs.get('composition_mode') is not True:
        return False
    finalization = snapshot.get('finalization', {})
    if finalization.get('composition_mode') is not True:
        return False
    values = dict(bridge['replacements'])
    pairs = [(inputs.get(field), values.get(token)) for field, token in _CURRENT_FIELDS.items()]
    pairs.append((inputs.get('action_frame'), bridge['frame']))
    if 'common_evidence_inputs' in snapshot:
        pairs.append((inputs, snapshot['common_evidence_inputs']))
    for field in ('action', 'staging_tags'):
        if field in finalization:
            pairs.append((inputs.get(field), finalization[field]))
    if 'replacements' in finalization:
        pairs.append((bridge['replacements'], finalization['replacements']))
    producer = bridge.get('producer_context')
    if producer is not None:
        if not isinstance(producer, Mapping):
            return False
        for field in ('context', 'character_palette'):
            if field in producer:
                pairs.append((inputs.get(field), producer[field]))
    return all(canonical_json_bytes(left) == canonical_json_bytes(right) for left, right in pairs)


def _owner(atom):
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


def _catalog_source(source):
    """Keep origin categories while discarding each catalog's selected key."""
    if source.domain == 'clothing' and source.field.startswith('character_palette.'):
        return 'character_palette'
    if source.catalog_key is None:
        return 'producer'
    if source.domain == 'scene':
        return 'background_defaults' if source.catalog_key == 'background_defaults' else 'location_pack'
    return {'clothing': 'selected_clothing_pack', 'subject': 'character_profile',
            'template': 'template_catalog', 'mood': 'mood_catalog'}.get(source.domain, 'catalog')


def _shape(component):
    trace = component.trace
    parts = {part.part_id: part for part in trace.parts} if trace else {}
    emitted = [parts[part_id] for part_id in trace.emitted_part_ids] if trace else []
    return {
        'constructor_id': trace.constructor_id if trace else 'unknown',
        'source_fields': [part.source.field for part in emitted],
        'catalog_sources': [_catalog_source(part.source) for part in emitted],
        'forms': [atom.form for atom in component.atoms],
        'attachments': [atom.attachment for atom in component.atoms],
        'owners': [_owner(atom) for atom in component.atoms],
        'grammar': [atom.grammar_known.value for atom in component.atoms],
        'runtime_available': component.runtime_available,
    }


def build_coverage_signature(snapshot: Mapping, diagnosis: Mapping) -> dict:
    """Rebuild common proof even on fallback; retain labelled legacy diagnostics otherwise."""
    families = diagnosis.get('families', {})
    result = {
        'schema_version': SCHEMA_VERSION,
        'route': diagnosis.get('route', 'fallback'),
        'proof_basis': 'legacy_diagnostic',
        'blocked_domains': sorted(name for name, value in diagnosis.get('domains', {}).items()
                                  if value.get('blockers') or value.get('runtime_available') is not True),
        'domains': {name: {'constructor_id': 'unknown', 'source_fields': [], 'catalog_sources': [],
                          'forms': [], 'attachments': [], 'owners': [], 'grammar': [],
                          'runtime_available': value.get('runtime_available') is True}
                    for name, value in sorted(diagnosis.get('domains', {}).items())},
        'eligible_families': sorted(name for name, value in families.items()
                                    if value.get('runtime_eligible') is True),
        'family_blockers': {name: sorted(set(value.get('blockers', ())))
                            for name, value in sorted(families.items())},
    }
    bridge = snapshot.get('bridge')
    if not isinstance(bridge, Mapping) or bridge.get('common_inputs') is None:
        return result
    inputs = bridge['common_inputs']
    try:
        if not _current_inputs(snapshot, bridge, inputs):
            raise ValueError('Common inputs do not match current snapshot')
        evidence = build_realization_evidence(inputs)
        proofs = prove_all_families(ContentPlan(**bridge['input_plan']), evidence, builder_inputs=inputs)
        shapes = {component.domain: _shape(component) for component in evidence.components}
    except (KeyError, TypeError, ValueError, AttributeError):
        result['proof_basis'] = 'invalid_common_inputs'
        result['eligible_families'] = []
        result['family_blockers'] = {
            name: sorted(set(blockers) | {'binding.current_input_mismatch'})
            for name, blockers in result['family_blockers'].items()}
        return result
    result.update(
        proof_basis='common_reconstructed', domains=dict(sorted(shapes.items())),
        blocked_domains=sorted(component.domain for component in evidence.components
                               if component.blockers or component.runtime_available is not True),
        eligible_families=sorted(proof.family for proof in proofs if proof.eligible is True),
        family_blockers={proof.family: sorted(set(proof.blocker_ids))
                         for proof in sorted(proofs, key=lambda proof: proof.family)},
    )
    return result


def coverage_signature_hash(signature: Mapping) -> str:
    return hashlib.sha256(canonical_json_bytes(signature)).hexdigest()
