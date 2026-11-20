"""Structured terminology, generated reading views and conservative, read-only checks."""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_TERMINOLOGY = Path(__file__).resolve().parents[1] / 'references/terminology.json'
# Mask protected syntax without joining visible words across it. This is not an ICU parser.
PROTECTED = re.compile(
    r'`[^`]*`|\{\{[^{}]*\}\}|\$\{[^{}]*\}|\$t\([^()]*\)|\{[\w.-]+\}'
    r'|%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[sdif]'
    r'|</?(?:[A-Za-z][\w:.-]*|\d+)(?:\s[^<>]*?)?/?>'
    r'|(?:https?://|www\.)[^\s<>]+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'
    r'|(?<!\w)(?:[A-Za-z]:[\\/]|\.{0,2}/)[\w./\\-]+'
    r'|\b[\w.-]+\.(?:json|ya?ml|properties|csv|xml|tsx?|jsx?|py|md)\b'
)
COMPLEX_FORMAT = re.compile(r'\{\s*[\w.-]+\s*,\s*(?:plural|select|selectordinal|number|date|time)\b')


def load(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key: ' + key)
            value[key] = item
        return value

    def reject(value):
        raise ValueError('Non-JSON constant: ' + value)

    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique, parse_constant=reject)


def strings(value, parts=()):
    if isinstance(value, str):
        yield '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts), value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, (*parts, key))
    elif isinstance(value, list):
        for key, item in enumerate(value):
            yield from strings(item, (*parts, key))


def visible(text):
    return html.unescape(PROTECTED.sub(lambda m: ' ' * len(m[0]), text))


def rules(document):
    if not isinstance(document, dict) or document.get('schemaVersion') != 1:
        raise ValueError('Unsupported terminology schemaVersion')
    if not isinstance(document.get('sections'), list):
        raise ValueError('Terminology sections must be a list')
    seen = set()
    result = []
    for section in document['sections']:
        if not isinstance(section, dict) or not isinstance(section.get('entries', []), list):
            raise ValueError('Invalid terminology section')
        for entry in section.get('entries', []):
            if not isinstance(entry, dict) or not all(isinstance(entry.get(f), str) for f in ('id', 'source', 'japanese', 'notes')):
                raise ValueError('Terminology entries need id, source, japanese and notes strings')
            identity = entry['id']
            if not isinstance(identity, str) or not identity or identity in seen:
                raise ValueError('Invalid or duplicate terminology id: ' + str(identity))
            seen.add(identity)
            if 'check' not in entry:
                continue
            rule = entry['check']
            if not isinstance(rule, dict) or set(rule) - {'kind', 'sourceTerms', 'match', 'severity', 'applications', 'deprecatedJapanese'}:
                raise ValueError('Invalid or unknown terminology check fields: ' + identity)
            if rule.get('kind') not in {'required', 'deprecated', 'context-dependent'}:
                raise ValueError('Unsupported terminology check: ' + identity)
            for field in ('sourceTerms',):
                if not isinstance(rule.get(field), list) or not rule[field] or not all(isinstance(x, str) and x.strip() for x in rule[field]):
                    raise ValueError('Nonempty sourceTerms required: ' + identity)
            if rule.get('match', 'phrase') not in {'phrase', 'exact'} or rule.get('severity', 'warning') not in {'error', 'warning'}:
                raise ValueError('Invalid terminology match/severity: ' + identity)
            if 'applications' in rule and (not isinstance(rule['applications'], list) or not rule['applications'] or not all(isinstance(x, str) and x for x in rule['applications'])):
                raise ValueError('Invalid terminology application scope: ' + identity)
            if rule['kind'] == 'deprecated' and (not isinstance(rule.get('deprecatedJapanese'), list) or not rule['deprecatedJapanese'] or not all(isinstance(x, str) and x for x in rule['deprecatedJapanese'])):
                raise ValueError('Deprecated Japanese variants required: ' + identity)
            if 'deprecatedJapanese' in rule and (not isinstance(rule['deprecatedJapanese'], list) or not rule['deprecatedJapanese'] or not all(isinstance(x, str) and x for x in rule['deprecatedJapanese'])):
                raise ValueError('Invalid deprecated Japanese variants: ' + identity)
            if rule['kind'] == 'required' and not entry['japanese'].strip():
                raise ValueError('Required Japanese must not be blank: ' + identity)
            result.append({**entry, 'check': rule})
    return result


def render(document):
    rules(document)
    lines = ['# ' + document['title'], '',
             'Generated from terminology.json. Maintain that JSON and run render_library.py; do not edit this reading view.', '']
    lines += document.get('introduction', []) + ['']
    for section in document['sections']:
        lines += ['## ' + section['title'], ''] + section.get('before', [])
        if section.get('before'):
            lines.append('')
        if section.get('entries'):
            lines += ['| ' + ' | '.join(section['columns']) + ' |', '|---|---|---|']
            for entry in section['entries']:
                cells = [entry['source'], entry['japanese'], entry['notes']]
                lines.append('| ' + ' | '.join(x.replace('|', '&#124;').replace('\n', '<br>') for x in cells) + ' |')
            lines.append('')
        lines += section.get('after', []) + ['']
    lines += ['## Executable coverage', '',
              'Checks are deliberately scoped. Error-level rules enforce explicit conventions; warning-level rules and unresolved context decisions require review. Unchecked glossary rows remain guidance. Longest source phrases win, so Invoice Date does not independently require Invoice. Protected syntax is excluded. See terminology-check.md for profiles, exceptions, limitations and exit codes.', '',
              '| Concept | Check | Source match | Level | Scope |', '|---|---|---|---|---|']
    for entry in rules(document):
        rule = entry['check']
        lines.append('| ' + ' | '.join([entry['source'], rule['kind'],
                     ', '.join(rule['sourceTerms']) + ' (' + rule.get('match', 'phrase') + ')',
                     rule.get('severity', 'warning'), ', '.join(rule.get('applications', ['all applications']))]) + ' |')
    return '\n'.join(lines).rstrip() + '\n'


def source_matches(text, entries):
    """Prefer longest non-overlapping phrases; retain separate occurrences elsewhere."""
    candidates = []
    for entry in entries:
        rule = entry['check']
        for term in rule['sourceTerms']:
            expression = r'(?<![\w-])' + re.escape(term).replace(r'\ ', r'\s+') + r'(?![\w-])'
            for match in re.finditer(expression, text, re.I):
                if rule.get('match') == 'exact' and ' '.join(text.split()).casefold() != ' '.join(term.split()).casefold():
                    continue
                candidates.append((match.start(), match.end(), entry['id'], entry))
    picked = []
    for start, end, _, entry in sorted(candidates, key=lambda row: (-(row[1] - row[0]), row[0], row[2])):
        if any(start == other_start and end == other_end and entry['id'] != other['id'] for other_start, other_end, other in picked):
            raise ValueError('Ambiguous overlapping terminology rules: ' + entry['source'])
        if any(start < other_end and end > other_start for other_start, other_end, _ in picked):
            continue
        picked.append((start, end, entry))
    return picked


def check(source, target, document, profile=None, application=None):
    entries = rules(document)
    profile = {} if profile is None else profile
    if not isinstance(profile, dict):
        raise ValueError('Profile must be an object')
    app = application or profile.get('application')
    if application and profile.get('application') and application != profile['application']:
        raise ValueError('Profile application differs from --application')
    policy = profile.get('terminology', {})
    if not isinstance(policy, dict) or set(policy) - {'decisionsByKey', 'exceptionsByKey', 'technicalByKey'}:
        raise ValueError('Unknown terminology profile fields')
    en, ja = dict(strings(source)), dict(strings(target))
    findings, decisions_used, exceptions_used, skipped = [], [], [], []
    all_entries = {e['id']: e for e in entries}
    by_key = {}
    for field in ('decisionsByKey', 'exceptionsByKey', 'technicalByKey'):
        mapping = policy.get(field, {})
        if not isinstance(mapping, dict):
            raise ValueError(field + ' must be an object')
        by_key[field] = mapping
        for key, records in mapping.items():
            if not isinstance(records, list) or not records:
                raise ValueError(field + ' entries must be nonempty lists: ' + key)
            identities = set()
            for record in records:
                if not isinstance(record, dict) or key not in en or key not in ja or record.get('source') != en[key] or record.get('target') != ja[key] or not record.get('reason'):
                    raise ValueError('Terminology record must bind exact source/target and reason: ' + key)
                identity = record.get('termId', 'technical')
                if identity in identities:
                    raise ValueError('Duplicate terminology record: ' + key)
                identities.add(identity)
                if field != 'technicalByKey' and identity not in all_entries:
                    raise ValueError('Unknown terminology termId: ' + str(identity))
                if field == 'decisionsByKey' and (all_entries[identity]['check']['kind'] != 'context-dependent' or record.get('status') not in {'provisional', 'confirmed', 'ai-reviewed'} or not record.get('meaning')):
                    raise ValueError('Context decision needs meaning and provisional/confirmed/ai-reviewed status: ' + key)
                if field == 'decisionsByKey' and record.get('status')=='ai-reviewed' and (not isinstance(record.get('reviewedBy'),str) or not record['reviewedBy'].strip() or not isinstance(record.get('evidence'),list) or not record['evidence'] or not all(isinstance(e,str) and e.strip() for e in record['evidence'])):
                    raise ValueError('AI-reviewed context needs reviewer and specific evidence: '+key)
                if field == 'exceptionsByKey' and (not isinstance(record.get('codes'), list) or not record['codes'] or not set(record['codes']) <= {'required-term-missing', 'deprecated-term', 'context-decision-needed'}):
                    raise ValueError('Exception needs specific terminology codes: ' + key)
    active = [e for e in entries if not e['check'].get('applications') or app in e['check']['applications']]
    scoped_candidates = [e for e in entries if e['check'].get('applications') and not app]
    unscoped = set()
    for key, english in en.items():
        if key not in ja:
            continue
        japanese = ja[key]
        if key in by_key['technicalByKey']:
            skipped.append({'key': key, 'reason': 'exact-pair technical record'})
            continue
        try:
            code_example = isinstance(json.loads(english), (dict, list))
        except (ValueError, TypeError):
            code_example = False
        if code_example:
            skipped.append({'key': key, 'reason': 'JSON object/array code example; structural review remains separate'})
            continue
        if COMPLEX_FORMAT.search(english) or COMPLEX_FORMAT.search(japanese):
            findings.append({'key': key, 'termId': None, 'code': 'format-review-needed', 'severity': 'warning', 'status': 'needs-review',
                             'message': 'Complex formatting needs parser-backed terminology review.'})
            continue
        text, translation = visible(english), visible(japanese)
        unscoped.update(entry['id'] for _, _, entry in source_matches(text, scoped_candidates))
        seen = set()
        for _, _, entry in source_matches(text, active):
            identity, rule = entry['id'], entry['check']
            if identity in seen:
                continue
            seen.add(identity)
            code = None
            if rule['kind'] == 'required' and entry['japanese'] not in translation:
                code = 'required-term-missing'
            if rule.get('deprecatedJapanese') and any(word in translation for word in rule['deprecatedJapanese']):
                code = 'deprecated-term'
            if rule['kind'] == 'context-dependent':
                decision = next((r for r in by_key['decisionsByKey'].get(key, []) if r['termId'] == identity), None)
                if decision:
                    decisions_used.append({'key': key, 'termId': identity, **decision})
                    continue
                code = 'context-decision-needed'
            if code:
                exception = next((r for r in by_key['exceptionsByKey'].get(key, []) if r['termId'] == identity and code in r['codes']), None)
                finding = {'key': key, 'termId': identity, 'code': code, 'severity': rule.get('severity', 'warning'),
                           'status': 'retained-with-specific-reason' if exception else 'needs-review',
                           'english': english, 'japanese': japanese, 'recommendedJapanese': entry['japanese'], 'message': entry['notes']}
                if exception:
                    finding['reason'] = exception['reason']
                    exceptions_used.append({'key': key, 'termId': identity})
                findings.append(finding)
    if unscoped:
        findings.append({'key': None, 'termId': None, 'code': 'application-scope-needed', 'severity': 'warning',
                         'status': 'needs-review', 'message': 'Supply --application or a profile to apply app-specific rules.', 'rules': sorted(unscoped)})
    open_findings = [f for f in findings if f['status'] == 'needs-review']
    missing, extra = sorted(en.keys() - ja.keys()), sorted(ja.keys() - en.keys())
    errors = sum(f['severity'] == 'error' for f in open_findings)
    provisional = sum(d['status'] == 'provisional' for d in decisions_used)
    return {'status': 'incomplete-input-pair' if missing or extra else 'failed' if errors else 'needs-review' if open_findings else 'passed-with-provisional-decisions' if provisional else 'passed-scoped-terminology-check',
            'application': app, 'counts': {'sourceStrings': len(en), 'targetStrings': len(ja), 'missingStrings': len(missing), 'extraStrings': len(extra),
            'errors': errors, 'warnings': len(open_findings) - errors, 'retainedFindings': len(exceptions_used),
            'contextDecisionsUsed': len(decisions_used), 'provisionalContextDecisions': sum(d['status'] == 'provisional' for d in decisions_used),
            'aiReviewedContextDecisions': sum(d['status'] == 'ai-reviewed' for d in decisions_used),
            'technicalStringsSkipped': len(skipped), 'activeRules': len(active), 'unscopedApplicationRules': len(unscoped)},
            'findingsByCode': dict(Counter(f['code'] for f in open_findings)), 'findings': findings,
            'contextDecisions': decisions_used, 'technicalStrings': skipped, 'missingKeys': missing, 'extraKeys': extra,
            'languageApproval': False, 'actualUILayoutChecked': False,
            'limitations': ['Curated rule coverage only; absence of a finding is not a full glossary or meaning review.',
                            'Context decisions and exceptions bind exact pairs; provisional decisions still need user confirmation.',
                            'Protected syntax is masked conservatively; custom formats and technical snippets need parser/context review.',
                            'Structural integrity, style, runtime rendering and Japanese-speaker approval are separate checks.']}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate the skill terminology reading view without a project library.')
    parser.add_argument('--terminology', default=str(DEFAULT_TERMINOLOGY))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(args.output).resolve() == Path(args.terminology).resolve():
        parser.error('Refusing to overwrite maintained terminology JSON')
    Path(args.output).write_text(render(load(args.terminology)), encoding='utf-8', newline='\n')
