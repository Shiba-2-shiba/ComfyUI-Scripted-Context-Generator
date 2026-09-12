"""Development reachability, not an Effective Diversity or adoption gate.

Exit codes: 0 valid audit, 1 replay/construction/parity failure, 2 input/source error.
Baseline source is executed in a separate isolated interpreter with its own imports.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
from tools.effective_diversity_signatures import build_semantic_signatures
from tools.prompt_quality_loop import build_source_manifest
from tools.realizer_reachability_diagnostics import diagnose_snapshot
from tools.workflow_prompt_runner import build_canonical_record, canonical_json_bytes
from workflow_widget_validation import load_workflow

CONTRACT_PATH = ROOT / 'docs/diversity_refactor/r43_metric_contract.json'
SCHEMA = 'realizer-reachability/v1'


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_bytes(canonical_json_bytes(value))


def source_identity():
    manifest = build_source_manifest(ROOT)
    inputs = ('prompts.jsonl', 'mood_map.json', 'templates.txt', 'assets/compatibility_review.csv',
              'pytest.ini', 'docs/diversity_refactor/spec.md', 'docs/diversity_refactor/r43_metric_contract.json')
    supplemental = {name: file_hash(ROOT / name) for name in inputs}
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    progress = (ROOT / 'docs/diversity_refactor/progress.md').read_text(encoding='utf-8')
    heading = '## 7. Locked Target / Guard Metrics'
    lock = heading + progress.split(heading, 1)[1].split('\n---', 1)[0]
    lock_hash = hashlib.sha256(lock.encode('utf-8')).hexdigest()
    if lock_hash != contract['a16_lock_sha256']:
        raise ValueError('A1.6 lock does not match the diagnostic contract')
    return {'manifest': manifest, 'supplemental_inputs': supplemental, 'a16_lock_sha256': lock_hash}


def builder_inputs(record):
    selector = record.get('output_selectors', {}).get('raw_prompt', {})
    traces = [t for t in record.get('execution_trace', []) if t.get('node_id') == selector.get('node_id')]
    if (selector.get('slot') != 0 or len(traces) != 1
            or traces[0].get('node_type') != 'ContextPromptBuilder'
            or traces[0].get('function') != 'build_prompt_context'):
        raise ValueError('invalid builder trace')
    inputs = traces[0]['inputs']
    if (type(inputs.get('seed')) is not int or type(inputs.get('composition_mode')) is not bool
            or not isinstance(inputs.get('template'), str)
            or json.loads(inputs['context_json']) != record['final_context']):
        raise ValueError('invalid builder inputs')
    return inputs


def compare_pair(baseline, current):
    left, right = baseline['record'], current['record']
    identity_fields = ('run_seed', 'base_workflow_hash', 'effective_workflow_hash', 'config_hash')
    if any(left.get(key) != right.get(key) for key in identity_fields):
        return {'status': 'NOT_COMPARABLE', 'mismatches': [], 'reason': 'workflow_cohort_or_config_changed'}
    mismatches = [key for key in ('raw_prompt', 'cleaned_prompt', 'final_context') if left[key] != right[key]]
    if baseline['builder_context'] != current['builder_context']:
        mismatches.append('builder_context')
    if not mismatches and baseline != current:
        mismatches.append('whole_record')
    return {'status': 'PASS' if not mismatches else 'FAIL', 'mismatches': mismatches}


def truth_counts(values):
    counts = Counter('true' if value is True else 'false' if value is False else 'unknown' for value in values)
    return {key: counts[key] for key in ('true', 'false', 'unknown')}


def summarize(rows):
    domains, families = {}, {}
    for name in sorted({name for row in rows for name in row.get('domains', {})}):
        values = [row['domains'][name] for row in rows if name in row.get('domains', {})]
        domains[name] = {field: truth_counts([value.get(field) for value in values])
                         for field in ('binding_success', 'constructor_supported', 'grammar_known',
                                       'runtime_available', 'audit_only', 'unknown')}
    ids = sorted({name for row in rows for name in row.get('families', {})})
    for name in ids:
        values = [row['families'][name] for row in rows if name in row.get('families', {})]
        families[name] = {field: sum(value.get(field) is True for value in values)
                          for field in ('declared', 'constructor_present', 'runtime_eligible', 'selected', 'executed_v2')}
        families[name].update({field: truth_counts([value.get(field) for value in values])
                               for field in ('constructor_v2', 'forced_render_v2')})
    counts, only, sets, pairs, triples = (Counter() for _ in range(5))
    examples = {}
    for row in sorted(rows, key=lambda row: row['run_seed']):
        for family, value in sorted(row.get('families', {}).items()):
            blocked = tuple(sorted(set(value['blockers'])))
            if not blocked:
                continue
            counts.update(blocked)
            if len(blocked) == 1:
                only.update(blocked)
            sets[blocked] += 1
            pairs.update(combinations(blocked, 2))
            triples.update(combinations(blocked, 3))
            for blocker in blocked:
                examples.setdefault(blocker, [])
                if len(examples[blocker]) < 3:
                    examples[blocker].append({'run_seed': row['run_seed'], 'family': family})
    def intersections(counter):
        return [{'blockers': list(keys), 'count': count} for keys, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]
    actual_v2, fallback = Counter(), Counter()
    for row in rows:
        normal = row.get('normal', {})
        family = normal.get('syntax_family')
        if normal.get('realizer_version') == 'v2':
            actual_v2[family] += 1
        elif normal.get('realizer_version') == 'v1':
            fallback[str(family)] += 1
    routes = Counter(row['route'] for row in rows)
    return {'domains': domains, 'families': families,
            'routes': {key: routes[key] for key in ('simple_legacy_compatible', 'legacy_direct', 'common_evidence', 'fallback')},
            'eligible_family_count_distribution': dict(sorted(Counter(str(sum(f.get('runtime_eligible') is True
                for f in row.get('families', {}).values())) for row in rows).items())),
            'blockers': {key: {'count': counts[key], 'only_blocked_by': only[key], 'examples': examples[key]}
                         for key in sorted(counts)},
            'blocker_combinations': intersections(sets), 'blocker_pairs': intersections(pairs),
            'blocker_triples': intersections(triples),
            'actual': {'v2_applied_count': sum(actual_v2.values()), 'v2_family_counts': dict(sorted(actual_v2.items())),
                       'v1_fallback_structure_counts': dict(sorted(fallback.items())),
                       'observed_structure_count': len(set(actual_v2) | set(fallback)),
                       'executed_v2_family_count': len(actual_v2),
                       'errors': [{'run_seed': row['run_seed'], **error} for row in sorted(rows, key=lambda row: row['run_seed'])
                                  for error in row.get('errors', [])]}}


_BASELINE_CODE = '''
import json, sys, hashlib
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(root))
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import build_canonical_record, canonical_json_bytes
from workflow_widget_validation import load_workflow
from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
before = build_source_manifest(root)
def supplemental():
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('prompts.jsonl','mood_map.json','templates.txt','assets/compatibility_review.csv')}
extras = supplemental()
workflow = load_workflow(root/'ComfyUI-workflow-context.json')
with (out/'baseline-pairs.jsonl').open('xb') as stream:
    for seed in range(int(sys.argv[3]), int(sys.argv[3])+int(sys.argv[4])):
        record = build_canonical_record(workflow, seed)
        selector = record['output_selectors']['raw_prompt']
        traces = [t for t in record['execution_trace'] if t['node_id']==selector['node_id']]
        assert len(traces)==1 and traces[0]['node_type']=='ContextPromptBuilder'
        inputs = traces[0]['inputs']
        context, text = build_prompt_from_context(context_from_json(inputs['context_json'],default_seed=inputs['seed']), inputs['template'], inputs['composition_mode'], inputs['seed'])
        assert text==record['raw_prompt']
        stream.write(canonical_json_bytes({'record':record,'builder_context':context.to_dict()}))
assert before==build_source_manifest(root) and extras==supplemental(), 'Baseline source changed'
(out/'baseline-identity.json').write_bytes(canonical_json_bytes({'source_tree_hash':before['source_tree_hash'],'supplemental_inputs':extras,'reachability':'NOT_AVAILABLE'}))
'''


def baseline_pairs(root, output, seed_start, sample_count):
    command = [sys.executable, '-I', '-B', '-c', _BASELINE_CODE, str(root.resolve()), str(output), str(seed_start), str(sample_count)]
    started = time.monotonic()
    with (output / 'baseline-process.log').open('xb') as log:
        result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, shell=False)
    write_json(output / 'baseline-command.json', {'command': command, 'cwd': str(root.resolve()),
               'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started})
    if result.returncode:
        raise ValueError('baseline execution failed; see baseline-process.log')
    return [json.loads(line) for line in (output / 'baseline-pairs.jsonl').read_text(encoding='utf-8').splitlines()]


def run_audit(args, output):
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    before = source_identity()
    write_json(output / 'source-manifest.json', before)
    workflow = load_workflow(ROOT / contract['workflow'])
    baseline = baseline_pairs(args.baseline_root, output, args.seed_start, args.sample_count) if args.baseline_root else None
    rows, comparisons = [], []
    record_hash, row_hash = hashlib.sha256(), hashlib.sha256()
    records_path, pairs_path = output / 'records.jsonl', output / 'normal-pairs.jsonl'
    with records_path.open('xb') as records, pairs_path.open('xb') as pairs:
        for index, seed in enumerate(range(args.seed_start, args.seed_start + args.sample_count)):
            record = build_canonical_record(workflow, seed)
            inputs = builder_inputs(record)
            context = context_from_json(inputs['context_json'], default_seed=inputs['seed'])
            kwargs = {'template': inputs['template'], 'composition_mode': inputs['composition_mode'], 'seed': inputs['seed']}
            rng_before, upstream = random.getstate(), context.to_dict()
            plain, plain_text = build_prompt_from_context(context, **kwargs)
            captured = []
            updated, raw = build_prompt_from_context(context, **kwargs, audit_sink=captured.append)
            errors = []
            if len(captured) != 1:
                raise ValueError('missing or ambiguous diagnostic snapshot')
            if raw != record['raw_prompt'] or plain_text != raw:
                errors.append({'id': 'binding.replay_mismatch'})
            if plain.to_dict() != updated.to_dict() or context.to_dict() != upstream:
                errors.append({'id': 'transport.sink_context_mismatch'})
            diagnostic = diagnose_snapshot(captured[0], force_families=args.force_families == 'all')
            if random.getstate() != rng_before:
                errors.append({'id': 'transport.rng_mismatch'})
            debug = updated.history[-1].decision
            projection = build_semantic_signatures(record, builder_decision=debug)
            row = {'run_seed': seed, 'builder_seed': inputs['seed'], **diagnostic,
                   'input_binding': {'builder_inputs_sha256': digest(inputs), 'source_tree_hash': before['manifest']['source_tree_hash']},
                   'normal': {'realizer_version': debug['realizer_version'], 'syntax_family': debug['syntax_family'],
                              'candidate_v2_applied': debug.get('candidate_v2_applied', False), 'raw_prompt': raw,
                              'cleaned_prompt': record['cleaned_prompt'], 'builder_context_sha256': digest(updated.to_dict()),
                              'upstream_context_sha256': digest(upstream), 'core': projection['core'], 'frame': projection['frame']},
                   'sink_parity': not errors, 'errors': diagnostic['errors'] + errors}
            pair = {'record': record, 'builder_context': updated.to_dict()}
            if baseline is not None:
                comparison = compare_pair(baseline[index], pair)
                comparisons.append({'run_seed': seed, **comparison})
                if comparison['status'] == 'FAIL':
                    row['errors'].append({'id': 'comparison.baseline_mismatch', 'fields': comparison['mismatches']})
            rows.append(row)
            encoded = canonical_json_bytes(record)
            records.write(encoded)
            record_hash.update(encoded)
            pairs.write(canonical_json_bytes(pair))
            if index % 128 == 0:
                print(f'audited {index + 1}/{args.sample_count}', flush=True)
    with (output / 'rows.jsonl').open('xb') as handle:
        for row in rows:
            encoded = canonical_json_bytes(row)
            handle.write(encoded)
            row_hash.update(encoded)
    after = source_identity()
    write_json(output / 'source-manifest-after.json', after)
    report = summarize(rows)
    status = 'invalid' if before != after else 'error' if report['actual']['errors'] else 'ok'
    comparison_report = None
    if baseline is not None:
        comparable = all(row['status'] != 'NOT_COMPARABLE' for row in comparisons)
        old_success = {item['record']['run_seed'] for item in baseline
                       if item['builder_context']['history'][-1]['decision']['realizer_version'] == 'v2'}
        new_success = {row['run_seed'] for row in rows if row['normal']['realizer_version'] == 'v2'}
        comparison_report = {'status': 'NOT_COMPARABLE' if not comparable else 'FAIL' if any(c['mismatches'] for c in comparisons) else 'PASS',
                             'baseline_identity': json.loads((output / 'baseline-identity.json').read_text(encoding='utf-8')),
                             'paired_count': len(comparisons), 'rows': comparisons,
                             'new_success_seeds': sorted(new_success - old_success) if comparable else None,
                             'preserved_success_seeds': sorted(new_success & old_success) if comparable else None,
                             'regressed_success_seeds': sorted(old_success - new_success) if comparable else None}
    with records_path.open('r', encoding='utf-8') as stream:
        first_record = json.loads(next(stream))
    git_commit = None
    git = ['git', '-c', f'safe.directory={ROOT.as_posix()}', '-C', str(ROOT)]
    top = subprocess.run([*git, 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if top.returncode == 0 and Path(top.stdout.strip()).resolve() == ROOT:
        git_commit = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
    report.update({'schema_version': SCHEMA, 'status': status, 'candidate_id': 'r43-audit-base',
                   'identity': {'git_commit': git_commit, 'source_tree_hash': before['manifest']['source_tree_hash'],
                                'source_identity_hash': digest(before),
                                'audit_implementation_hash': digest({name: file_hash(ROOT / 'tools' / name)
                                    for name in ('audit_realizer_reachability.py', 'realizer_reachability_diagnostics.py')}),
                                'workflow_hash': first_record['base_workflow_hash'],
                                'effective_workflow_hash': first_record['effective_workflow_hash'],
                                'runner_config_hash': first_record['config_hash'],
                                'family_catalog_hash': file_hash(ROOT / 'vocab/data/natural_language_realizer_v2.json'),
                                'r43_contract_hash': file_hash(CONTRACT_PATH), 'a16_lock_id': contract['a16_lock_id']},
                   'cohort': {'seed_start': args.seed_start, 'sample_count': args.sample_count,
                              'history_mode': 'existing-workflow', 'classification': 'development-not-holdout'},
                   'force_families': args.force_families, 'records_sha256': record_hash.hexdigest(),
                   'rows_sha256': row_hash.hexdigest(), 'comparison': comparison_report,
                   'audit_only_replay': 'NOT_RUN', 'adoption_verdict': 'NOT_EVALUATED'})
    write_json(output / 'reachability.json', report)
    lines = ['# R43 development reachability', '', f'Status: {status}; samples: {len(rows)}.',
             f"Ordinary v2: {report['actual']['v2_applied_count']}/{len(rows)}; executed families: {report['actual']['executed_v2_family_count']}; structures including fallback: {report['actual']['observed_structure_count']}.", '',
             '| Family | Eligible | Forced constructor v2 | Certified forced v2 | Selected | Executed v2 |',
             '|---|---:|---:|---:|---:|---:|']
    for key, value in report['families'].items():
        constructor, certified = 'NOT_RUN', 'NOT_RUN'
        if args.force_families == 'all' and value['runtime_eligible']:
            constructor = str(value['constructor_v2']['true'])
            unknown = value['runtime_eligible'] - value['forced_render_v2']['true'] - value['forced_render_v2']['false']
            certified = f"{value['forced_render_v2']['true']} certified; {unknown} UNKNOWN"
        lines.append(f"| {key} | {value['runtime_eligible']} | {constructor} | {certified} | {value['selected']} | {value['executed_v2']} |")
    lines += ['', 'Unknown forced semantic proof is excluded; raw constructor success is a separate diagnostic.',
              'Blocker counts use seed-family rows and overlap; singleton counts are candidate upper bounds, not promised rescues.',
              'Audit-only producer replay is NOT_RUN. Adoption is not evaluated.']
    (output / 'reachability-summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return 2 if status == 'invalid' else 1 if status == 'error' else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('smoke', 'intake'), default='smoke')
    parser.add_argument('--seed-start', type=int, default=0)
    parser.add_argument('--sample-count', type=int)
    parser.add_argument('--force-families', choices=('none', 'all'), default='none')
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.sample_count is None:
        args.sample_count = 16 if args.profile == 'smoke' else 512
    output = args.output_dir.resolve()
    started = time.monotonic()
    try:
        if args.sample_count <= 0 or args.seed_start < 0:
            raise ValueError('sample count must be positive and seed start nonnegative')
        if args.baseline_root and not args.baseline_root.is_dir():
            raise ValueError('baseline root does not exist')
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        code = run_audit(args, output)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        write_json(output / 'error.json', {'status': 'error', 'type': type(error).__name__, 'detail': str(error)})
        print(str(error), file=sys.stderr)
        code = 2
    write_json(output / 'environment.json', {'python': sys.version, 'executable': sys.executable,
               'cwd': str(ROOT), 'output_dir': str(output), 'elapsed_seconds': time.monotonic() - started,
               'arguments': list(argv) if argv is not None else sys.argv[1:], 'exit_code': code})
    return code


if __name__ == '__main__':
    raise SystemExit(main())
