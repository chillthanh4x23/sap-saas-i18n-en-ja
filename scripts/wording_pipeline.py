#!/usr/bin/env python3
"""Local JSON i18n extraction, wording review, compilation and assembly. No translation API calls."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def reject_non_json_constant(value):
    raise ValueError('Non-JSON numeric constant: ' + value)


def load(filename):
    return json.loads(Path(filename).read_text(encoding='utf-8-sig'), object_pairs_hook=reject_duplicate_keys, parse_constant=reject_non_json_constant)


def resource(filename):
    value = load(filename)
    if not isinstance(value, (dict, list)):
        raise ValueError('An i18n resource must be a JSON object or array')
    return value


def save(filename, value):
    p = Path(filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def pointer(parts):
    return '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def strings(value, parts=()):
    if isinstance(value, str):
        yield {'parts': list(parts), 'key': pointer(parts), 'text': value}
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, (*parts, key))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from strings(child, (*parts, key))


def stable_id(prefix, text):
    return prefix + digest(text.encode('utf-8'))[:20]


TOKEN_RE = re.compile(r'\{\{[^{}]*\}\}|\$\{[^{}]*\}|\{[\w.-]+\}')
TYPED_RE = re.compile(r'\{[\w.-]+\s*,\s*[A-Za-z]+\s*[,}]')
JAPANESE_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')


def token_signature(text):
    return Counter(TOKEN_RE.findall(text))


def pair_quality(source, target):
    findings = []
    if target is None or (source.strip() and not target.strip()):
        findings.append('missing-or-blank-reference')
    elif TYPED_RE.search(source) or TYPED_RE.search(target):
        findings.append('external-formatter-review-required')
    elif token_signature(source) != token_signature(target):
        findings.append('placeholder-mismatch')
    return findings


def extract(project_root, manifest_file, output, validator=None):
    root, out = Path(project_root).resolve(), Path(output).resolve()
    manifest = load(manifest_file)
    grouped, occurrences, inputs, qa_summary, unpaired_targets = {}, [], [], [], []
    seen_pairs = set()
    for pair in manifest['pairs']:
        if pair['id'] in seen_pairs:
            raise ValueError('Duplicate manifest pair ID')
        seen_pairs.add(pair['id'])
        en_path, ja_path = root / pair['en'], root / pair['ja']
        en, ja = resource(en_path), resource(ja_path)
        en_rows, ja_rows = list(strings(en)), {x['key']: x['text'] for x in strings(ja)}
        en_keys = {x['key'] for x in en_rows}
        for key in sorted(set(ja_rows) - en_keys):
            unpaired_targets.append({'pair': pair['id'], 'targetFile': pair['ja'], 'key': key,
                                     'japanese': ja_rows[key], 'reason': 'No English string at this path in the paired source; not silently added to the wording dictionary.'})
        external_findings = defaultdict(list)
        if validator:
            proc = subprocess.run(['node', str(validator), str(en_path), str(ja_path), '--json'], capture_output=True, text=True, encoding='utf-8')
            if proc.returncode not in (0, 1):
                raise ValueError(f'Reference validator failed: {pair["id"]}: {proc.stdout} {proc.stderr}')
            report = json.loads(proc.stdout)
            for issue in report['issues']:
                if issue['severity'] == 'error':
                    external_findings[issue['key']].append(issue['code'])
            qa_summary.append({'pair': pair['id'], 'counts': report['counts']})
        for file in (en_path, ja_path):
            inputs.append({'path': str(file.relative_to(root)).replace('\\', '/'), 'sha256': digest(file.read_bytes())})
        for row in en_rows:
            text, target = row['text'], ja_rows.get(row['key'])
            entry_id = stable_id('w_', text)
            group = grouped.setdefault(text, {'entryId': entry_id, 'english': text, 'candidates': {}, 'occurrenceIds': []})
            if group['english'] != text:
                raise ValueError('Wording ID collision')
            oid = stable_id('o_', pair['id'] + '\0' + row['key'])
            errors = pair_quality(text, target)
            for issue_key, codes in external_findings.items():
                if issue_key == row['key'] or (issue_key and row['key'].startswith(issue_key + '/')):
                    errors.extend(codes)
            errors = sorted(set(errors))
            state = ('missing-reference' if target is None else 'broken-reference' if errors else
                     'identical-source-target' if target == text else
                     'translation-candidate' if JAPANESE_RE.search(target) else 'non-japanese-reference')
            record = {'occurrenceId': oid, 'entryId': entry_id, 'application': pair['application'], 'pair': pair['id'],
                      'sourceFile': pair['en'], 'targetFile': pair['ja'], 'key': row['key'], 'parts': row['parts'],
                      'english': text, 'japanese': target, 'referenceState': state, 'integrityFindings': errors}
            occurrences.append(record)
            group['occurrenceIds'].append(oid)
            if target is not None:
                cid = stable_id('c_', text + '\0' + target)
                candidate = group['candidates'].setdefault(target, {'candidateId': cid, 'japanese': target, 'occurrenceIds': [], 'usableOccurrenceIds': []})
                candidate['occurrenceIds'].append(oid)
                if not errors:
                    candidate['usableOccurrenceIds'].append(oid)
    entries = []
    for group in grouped.values():
        group['candidates'] = list(group['candidates'].values())
        group['hasMultipleJapaneseValues'] = len(group['candidates']) > 1
        group['reviewStatus'] = 'unreviewed-reference-suggestions'
        entries.append(group)
    entries.sort(key=lambda x: x['entryId'])
    states = Counter(x['referenceState'] for x in occurrences)
    summary = {'sourceStringOccurrences': len(occurrences), 'uniqueExactEnglishTexts': len(entries),
               'duplicateOccurrencesBeyondFirst': len(occurrences) - len(entries),
               'repeatedTextGroups': sum(len(e['occurrenceIds']) > 1 for e in entries),
               'textsWithMultipleJapaneseValues': sum(e['hasMultipleJapaneseValues'] for e in entries),
               'referenceStates': dict(states), 'unpairedTargetStrings': len(unpaired_targets)}
    library = {'schemaVersion': 1, 'status': 'reference-suggestions-not-approved-translations', 'summary': summary, 'entries': entries}
    save(out / 'library/candidates.json', library)
    (out / 'library/source-occurrences.jsonl').write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in occurrences), encoding='utf-8', newline='\n')
    save(out / 'library/source-manifest.json', {'schemaVersion': 1, 'inputs': inputs, 'referenceChecks': qa_summary})
    save(out / 'library/unpaired-target-strings.json', {'schemaVersion': 1, 'items': unpaired_targets})
    return summary


def plan(project_root, source_file, application, library_dir, output):
    root, lib = Path(project_root).resolve(), Path(library_dir)
    src_path = (root / source_file).resolve()
    if Path(output).resolve() in {src_path, (lib / 'candidates.json').resolve(), (lib / 'source-occurrences.jsonl').resolve()}:
        raise ValueError('Refusing to overwrite a planning input')
    source = resource(src_path)
    entries = {e['english']: e for e in load(lib / 'candidates.json')['entries']}
    occurrences = {o['occurrenceId']: o for o in map(json.loads, (lib / 'source-occurrences.jsonl').read_text(encoding='utf-8').splitlines())}
    groups = {}
    for row in strings(source):
        group = groups.setdefault(row['text'], {'entryId': stable_id('w_', row['text']), 'english': row['text'], 'targetKeys': [], 'targetParts': []})
        group['targetKeys'].append(row['key'])
        group['targetParts'].append(row['parts'])
    result = []
    for text, group in groups.items():
        candidates = []
        for c in entries.get(text, {}).get('candidates', []):
            provenance = [occurrences[oid] for oid in c['occurrenceIds']]
            usable = [o for o in provenance if o['occurrenceId'] in c['usableOccurrenceIds']]
            score = max((100 if o['application'] == application and o['key'] in group['targetKeys'] else 50 if o['application'] == application else 10 for o in usable), default=0)
            candidates.append({**c, 'contextScore': score, 'provenance': [{'application': o['application'], 'pair': o['pair'], 'key': o['key'], 'state': o['referenceState'], 'findings': o['integrityFindings']} for o in provenance]})
        candidates.sort(key=lambda c: (-c['contextScore'], c['candidateId']))
        group['candidates'] = candidates
        group['decisionStatus'] = 'requires-review'
        result.append(group)
    doc = {'schemaVersion': 1, 'application': application, 'sourceFile': source_file, 'sourceSha256': digest(src_path.read_bytes()),
           'summary': {'sourceStrings': sum(len(g['targetKeys']) for g in result), 'uniqueReviewItems': len(result),
                       'itemsWithCandidates': sum(bool(g['candidates']) for g in result),
                       'itemsWithMultipleCandidates': sum(len(g['candidates']) > 1 for g in result)}, 'items': result}
    save(output, doc)
    return doc['summary']


def compile_library(plan_file, decisions_file, output_library, output_mapping):
    inputs = {Path(plan_file).resolve(), Path(decisions_file).resolve()}
    outputs = [Path(output_library).resolve(), Path(output_mapping).resolve()]
    if outputs[0] == outputs[1] or any(p in inputs for p in outputs):
        raise ValueError('Compilation outputs must be distinct from each other and from review inputs')
    work, decisions = load(plan_file), load(decisions_file)
    if decisions.get('worklistSha256') != digest(Path(plan_file).read_bytes()):
        raise ValueError('Worklist changed since review; existing decisions cannot approve new contexts automatically')
    if decisions.get('application') != work['application']:
        raise ValueError('Decision application differs from worklist scope')
    selected = defaultdict(list)
    for d in decisions['items']:
        selected[d['entryId']].append(d)
    expected = {x['entryId'] for x in work['items']}
    if set(selected) != expected:
        raise ValueError('Review decisions must cover the exact worklist, without missing or extra entries')
    entries, mapping = [], []
    for item in work['items']:
        covered = set()
        parts_by_key = dict(zip(item['targetKeys'], item['targetParts']))
        candidate_ids = {c['candidateId']: c for c in item['candidates']}
        for d in selected[item['entryId']]:
            keys = d.get('targetKeys', item['targetKeys'])
            if not isinstance(keys, list) or not keys or any(not isinstance(k, str) for k in keys):
                raise ValueError('Context keys must be a nonempty list of source paths')
            if len(set(keys)) != len(keys) or not set(keys) <= set(item['targetKeys']) or covered.intersection(keys):
                raise ValueError('Overlapping or unknown context keys')
            covered.update(keys)
            if d['english'] != item['english']:
                raise ValueError('Source wording changed since review')
            ja = d['japanese']
            if not isinstance(ja, str) or (item['english'].strip() and not ja.strip()):
                raise ValueError('Missing Japanese decision')
            if d.get('reviewStatus') not in ('ai-reviewed', 'user-authorized-provisional'):
                raise ValueError('An unresolved or unreviewed decision cannot be compiled')
            if d['reviewStatus'] == 'user-authorized-provisional' and not d.get('authorization'):
                raise ValueError('Provisional wording requires authorization evidence')
            if (item['english'] == ja or (re.search(r'[A-Za-z]', ja) and not JAPANESE_RE.search(ja))) and not d.get('retentionReason'):
                raise ValueError('English/technical retention requires an explicit retention reason')
            if pair_quality(item['english'], ja):
                raise ValueError('Decision changes placeholders or requires unsupported format review: ' + item['entryId'])
            for cid in d.get('referenceCandidateIds', []):
                if cid not in candidate_ids or not candidate_ids[cid]['usableOccurrenceIds']:
                    raise ValueError('Unknown or broken reference candidate used as evidence')
            if not d.get('reviewNote'):
                raise ValueError('A decision must record why it is suitable in context')
            context_key = json.dumps(sorted(keys), ensure_ascii=False)
            selection_id = stable_id('s_', work['application'] + '\0' + item['entryId'] + '\0' + context_key)
            entry = {'entryId': item['entryId'], 'selectionId': selection_id, 'english': item['english'], 'japanese': ja,
                     'scope': {'application': work['application'], 'reviewedKeys': keys},
                     'reviewStatus': d['reviewStatus'], 'reviewNote': d['reviewNote'],
                     'referenceCandidateIds': d.get('referenceCandidateIds', []), 'basis': d['basis']}
            for field in ('retentionReason', 'authorization', 'optimizationReason'):
                if d.get(field):
                    entry[field] = d[field]
            entries.append(entry)
            for key in keys:
                mapping.append({'key': key, 'parts': parts_by_key[key], 'english': item['english'], 'entryId': item['entryId'], 'selectionId': selection_id})
        if covered != set(item['targetKeys']):
            raise ValueError('Context decisions leave source keys uncovered')
    library = {'schemaVersion': 1, 'sourceLocale': 'en', 'targetLocale': 'ja', 'status': 'AI-reviewed-prototype-not-native-approved',
               'applicationScope': work['application'], 'entries': entries}
    save(output_library, library)
    map_doc = {'schemaVersion': 1, 'application': work['application'], 'sourceFile': work['sourceFile'], 'sourceSha256': work['sourceSha256'],
               'librarySha256': digest(Path(output_library).read_bytes()), 'entries': mapping}
    save(output_mapping, map_doc)
    return {'reviewedWordings': len(entries), 'mappedSourceKeys': len(mapping), 'reviewStatuses': dict(Counter(e['reviewStatus'] for e in entries)), 'decisionBasis': dict(Counter(e['basis'] for e in entries))}


def assemble(project_root, source_file, library_file, mapping_file, output):
    src = (Path(project_root) / source_file).resolve()
    dest = Path(output).resolve()
    protected = {src, Path(library_file).resolve(), Path(mapping_file).resolve()}
    if dest in protected:
        raise ValueError('Refusing to overwrite a source, library or mapping input')
    library, mapping = load(library_file), load(mapping_file)
    if mapping['sourceSha256'] != digest(src.read_bytes()):
        raise ValueError('Source changed since mapping was reviewed; rebuild the worklist')
    if mapping['librarySha256'] != digest(Path(library_file).read_bytes()):
        raise ValueError('Library changed since mapping was compiled')
    if src != (Path(project_root) / mapping['sourceFile']).resolve():
        raise ValueError('Mapping belongs to a different source file')
    source = resource(src)
    expected = {r['key']: r for r in strings(source)}
    selections = {e['selectionId']: e for e in library['entries']}
    mapped = {}
    for row in mapping['entries']:
        if row['key'] in mapped:
            raise ValueError('Duplicate mapped key')
        mapped[row['key']] = row
    if set(mapped) != set(expected):
        raise ValueError('Mapping does not cover the exact source key set')
    result = copy.deepcopy(source)
    for key, row in mapped.items():
        original = expected[key]
        e = selections.get(row['selectionId'])
        if not e or row['english'] != original['text'] or row['parts'] != original['parts']:
            raise ValueError('Invalid source/mapping association')
        if e['entryId'] != row['entryId'] or e['english'] != original['text'] or e['scope']['application'] != mapping['application'] or key not in e['scope']['reviewedKeys']:
            raise ValueError('Library entry does not cover this application/key context')
        current = result
        for part in row['parts'][:-1]:
            current = current[part]
        current[row['parts'][-1]] = e['japanese']
    save(dest, result)
    retained = sum(expected[k]['text'] == selections[r['selectionId']]['japanese'] for k, r in mapped.items())
    return {'sourceStrings': len(expected), 'filledFromReviewedLibrary': len(mapped), 'intentionallyRetained': retained, 'missingStrings': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('extract')
    p.add_argument('--project-root', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--validator')
    p = sub.add_parser('plan')
    p.add_argument('--project-root', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--application', required=True)
    p.add_argument('--library-dir', required=True)
    p.add_argument('--output', required=True)
    p = sub.add_parser('compile')
    p.add_argument('--plan', required=True)
    p.add_argument('--decisions', required=True)
    p.add_argument('--output-library', required=True)
    p.add_argument('--output-mapping', required=True)
    p = sub.add_parser('assemble')
    p.add_argument('--project-root', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--library', required=True)
    p.add_argument('--mapping', required=True)
    p.add_argument('--output', required=True)
    a = parser.parse_args()
    if a.command == 'extract':
        result = extract(a.project_root, a.manifest, a.output, a.validator)
    elif a.command == 'plan':
        result = plan(a.project_root, a.source, a.application, a.library_dir, a.output)
    elif a.command == 'compile':
        result = compile_library(a.plan, a.decisions, a.output_library, a.output_mapping)
    else:
        result = assemble(a.project_root, a.source, a.library, a.mapping, a.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
