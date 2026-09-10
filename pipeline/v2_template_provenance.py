"""Bind source template topology before preserving a scene wrapper as finite.

These functions prove the wrapper only. The caller must independently prove the
locative scene's constituents before materialization; source membership cannot
establish their grammar or attachment.
"""
from collections.abc import Mapping
import re

try:
    from ..vocab.loader import load_json
except ImportError:
    from vocab.loader import load_json


_OWNED_SCENE = re.compile(
    r'(?:and|with) (?P<owner>the (?:room|scene) around her) staying in '
    r'\{scene_anchor_clause\}'
)


def scene_template_kind(slots):
    """Classify an exact catalog triple with independently known slot grammar."""
    if not isinstance(slots, Mapping):
        return None
    if slots.get('subject') != '{subject_clause}' or slots.get('adjunct') != '{action_clause}':
        return None
    scene = slots.get('scene')
    if not isinstance(scene, str):
        return None
    if scene == '{scene_clause}':
        kind = 'direct'
    elif _OWNED_SCENE.fullmatch(scene):
        kind = 'owned_finite'
    else:
        return None
    catalog = load_json('template_catalog.json')
    if not isinstance(catalog, Mapping):
        return None
    for slot, field in (('subject', 'intro'), ('adjunct', 'body'), ('scene', 'end')):
        entries = catalog.get(field)
        if not isinstance(entries, (list, tuple)) or not any(
            isinstance(entry, Mapping) and entry.get('text') == slots[slot]
            for entry in entries
        ):
            return None
    return kind


def materialize_scene_template(slots, locative_scene):
    """Preserve proved scene text, changing only a link and staying's inflection."""
    kind = scene_template_kind(slots)
    if (kind is None or not isinstance(locative_scene, str)
            or not locative_scene or locative_scene.strip() != locative_scene
            or re.search(r'[{}.!?;\r\n]', locative_scene)):
        return None
    if kind == 'direct':
        # Existing direct constructors also produce 'on' for road/street.
        # This checks the wrapper boundary only; noun proof remains upstream.
        return locative_scene if re.fullmatch(r'(?:in|on) [^\s].*', locative_scene) else None
    if not locative_scene.startswith('in ') or not locative_scene[3:] or locative_scene[3:].strip() != locative_scene[3:]:
        return None
    owner = _OWNED_SCENE.fullmatch(slots['scene']).group('owner')
    return owner + ' stays ' + locative_scene
