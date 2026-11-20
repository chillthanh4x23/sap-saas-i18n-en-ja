import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('terminology_gate', SCRIPTS / 'terminology.py')
terms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terms)


def entry(identity, source, japanese, kind='required', **check):
    return {'id': identity, 'source': source, 'japanese': japanese, 'notes': 'Fixture meaning.',
            'check': {'kind': kind, 'sourceTerms': [source], 'severity': 'error' if kind == 'required' else 'warning', **check}}


def document(*entries):
    return {'schemaVersion': 1, 'title': 'Test glossary', 'sections': [
        {'title': 'Terms', 'columns': ['English', 'Japanese', 'Notes'], 'entries': list(entries)}]}


class TerminologyTests(unittest.TestCase):
    def setUp(self):
        self.draft = entry('draft', 'Draft', 'ドラフト', deprecatedJapanese=['下書き'])
        self.item = entry('item', 'Item', '品目 / 明細 / 項目', 'context-dependent')
        self.doc = document(self.draft, self.item)

    def test_required_term_is_checked_in_compounds(self):
        result = terms.check({'a': 'Generate Draft'}, {'a': '下書きを生成'}, self.doc)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['findingsByCode'], {'deprecated-term': 1})

    def test_missing_required_term_fails(self):
        self.assertEqual(terms.check({'a': 'Draft'}, {'a': '未完成'}, self.doc)['counts']['errors'], 1)

    def test_required_and_deprecated_word_together_still_fails(self):
        self.assertEqual(terms.check({'a': 'Draft'}, {'a': 'ドラフト（下書き）'}, self.doc)['status'], 'failed')

    def test_current_term_passes_without_rewriting_inputs(self):
        en, ja = {'a': 'Draft'}, {'a': 'ドラフト'}
        before = copy.deepcopy((en, ja, self.doc))
        self.assertEqual(terms.check(en, ja, self.doc)['status'], 'passed-scoped-terminology-check')
        self.assertEqual((en, ja, self.doc), before)

    def test_context_term_never_forces_one_translation(self):
        result = terms.check({'a': 'Item'}, {'a': '明細'}, self.doc)
        self.assertEqual(result['findingsByCode'], {'context-decision-needed': 1})
        self.assertEqual(result['counts']['errors'], 0)

    def context_profile(self, status='provisional'):
        return {'terminology': {'decisionsByKey': {'/a': [{'termId': 'item', 'source': 'Item', 'target': '明細',
                'meaning': 'Document line item', 'reason': 'Invoice detail row', 'status': status}]}}}

    def test_provisional_context_stays_explicit(self):
        result = terms.check({'a': 'Item'}, {'a': '明細'}, self.doc, self.context_profile())
        self.assertEqual(result['status'], 'passed-with-provisional-decisions')
        self.assertEqual(result['counts']['provisionalContextDecisions'], 1)

    def test_confirmed_context_resolves_review(self):
        self.assertEqual(terms.check({'a': 'Item'}, {'a': '明細'}, self.doc, self.context_profile('confirmed'))['counts']['warnings'], 0)

    def test_ai_reviewed_context_requires_reviewer_and_evidence(self):
        profile = self.context_profile('ai-reviewed')
        with self.assertRaisesRegex(ValueError, 'reviewer'):
            terms.check({'a':'Item'}, {'a':'明細'}, self.doc, profile)
        profile['terminology']['decisionsByKey']['/a'][0].update(reviewedBy='Fixture AI', evidence=['Invoice line table namespace.'])
        result=terms.check({'a':'Item'}, {'a':'明細'}, self.doc, profile)
        self.assertEqual(result['counts']['aiReviewedContextDecisions'],1)

    def test_context_decision_rejects_changed_source_or_target(self):
        for en, ja in [('Items', '明細'), ('Item', '品目')]:
            with self.subTest(en=en, ja=ja), self.assertRaisesRegex(ValueError, 'exact source/target'):
                terms.check({'a': en}, {'a': ja}, self.doc, self.context_profile())

    def test_exact_exception_is_specific_and_stale_exception_fails(self):
        profile = {'terminology': {'exceptionsByKey': {'/a': [{'termId': 'draft', 'source': 'Draft', 'target': '下書き',
                   'codes': ['deprecated-term'], 'reason': 'Frozen historical test only.'}]}}}
        result = terms.check({'a': 'Draft'}, {'a': '下書き'}, self.doc, profile)
        self.assertEqual(result['counts']['retainedFindings'], 1)
        with self.assertRaises(ValueError):
            terms.check({'a': 'Draft'}, {'a': '別の訳'}, self.doc, profile)

    def test_exception_does_not_hide_other_codes(self):
        profile = {'terminology': {'exceptionsByKey': {'/a': [{'termId': 'draft', 'source': 'Draft', 'target': '下書き',
                   'codes': ['required-term-missing'], 'reason': 'Wrong code must not suppress.'}]}}}
        self.assertEqual(terms.check({'a': 'Draft'}, {'a': '下書き'}, self.doc, profile)['counts']['errors'], 1)

    def test_longest_phrase_does_not_require_shorter_concept(self):
        doc = document(entry('invoice', 'Invoice', '請求書'), entry('invoice-date', 'Invoice Date', '請求日'))
        self.assertEqual(terms.check({'a': 'Invoice Date'}, {'a': '請求日'}, doc)['counts']['errors'], 0)
        self.assertEqual(terms.check({'a': 'Invoice Date / Invoice'}, {'a': '請求日'}, doc)['counts']['errors'], 1)

    def test_boundaries_avoid_technical_identifiers(self):
        for source in ['draftId', 'DRAFT_STATUS', 'draft-mode', 'overdraft']:
            with self.subTest(source=source):
                self.assertEqual(terms.check({'a': source}, {'a': source}, self.doc)['counts']['errors'], 0)

    def test_exact_rule_does_not_apply_to_longer_sentence(self):
        doc = document(entry('invoice-date', 'Invoice Date', '請求日', match='exact'))
        self.assertEqual(terms.check({'a': 'Check invoice date'}, {'a': '日付を確認'}, doc)['counts']['errors'], 0)

    def test_placeholders_urls_code_and_attributes_are_excluded(self):
        for source in ['{{draft}}', '${draft}', '{draft}', '$t(draft)', '`Draft`', 'https://example.test/draft', '/draft/file.json', 'Draft.json', '{"Draft":"sample"}', '<span title="Draft">Name</span>']:
            with self.subTest(source=source):
                self.assertEqual(terms.check({'a': source}, {'a': source}, self.doc)['counts']['errors'], 0)

    def test_target_placeholder_does_not_satisfy_visible_requirement(self):
        self.assertEqual(terms.check({'a': 'Draft {{ドラフト}}'}, {'a': '{{ドラフト}}'}, self.doc)['counts']['errors'], 1)

    def test_complex_format_is_explicitly_unchecked(self):
        result = terms.check({'a': '{count, plural, other {Draft}}'}, {'a': '{count, plural, other {ドラフト}}'}, self.doc)
        self.assertEqual(result['findingsByCode'], {'format-review-needed': 1})

    def test_app_scope_is_respected(self):
        doc = document(entry('vector', 'Vector', 'ベクトル', 'deprecated', deprecatedJapanese=['ベクター'], applications=['ExampleApp']))
        self.assertEqual(terms.check({'a': 'Vector'}, {'a': 'ベクター'}, doc, application='ExampleApp')['counts']['warnings'], 1)
        self.assertEqual(terms.check({'a': 'Vector'}, {'a': 'ベクター'}, doc, application='OTHER')['counts']['warnings'], 0)
        self.assertIn('application-scope-needed', terms.check({'a': 'Vector'}, {'a': 'ベクター'}, doc)['findingsByCode'])

    def test_profile_app_mismatch_fails(self):
        with self.assertRaises(ValueError):
            terms.check({}, {}, self.doc, {'application': 'A'}, 'B')

    def test_missing_app_only_warns_when_scoped_concept_occurs(self):
        doc = document(entry('vector', 'Vector', 'ベクトル', 'deprecated', deprecatedJapanese=['ベクター'], applications=['ExampleApp']))
        self.assertEqual(terms.check({'a': 'Name'}, {'a': '名前'}, doc)['counts']['warnings'], 0)
        self.assertEqual(terms.check({'a': '{"Vector":"sample"}'}, {'a': '{"Vector":"sample"}'}, doc)['counts']['warnings'], 0)

    def test_ambiguous_matching_rules_are_rejected(self):
        doc = document(entry('a', 'Draft', 'ドラフト'), entry('b', 'Draft', '下書き'))
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            terms.check({'a': 'Draft'}, {'a': 'ドラフト'}, doc)

    def test_invalid_profile_and_rule_types_are_rejected(self):
        for profile in [[], 'bad', {'terminology': []}]:
            with self.assertRaises(ValueError):
                terms.check({}, {}, self.doc, profile)
        for doc in [{'schemaVersion': 1, 'sections': 'bad'}, document({'id': 'x'}), document({**self.draft, 'check': []})]:
            with self.assertRaises(ValueError):
                terms.rules(doc)

    def test_missing_extra_and_escaped_array_keys(self):
        result = terms.check({'a/b': ['Draft']}, {'extra': 'ドラフト'}, self.doc)
        self.assertEqual(result['status'], 'incomplete-input-pair')
        self.assertEqual(result['missingKeys'], ['/a~1b/0'])

    def test_invalid_rules_and_unknown_profile_fields_are_rejected(self):
        for doc in [document(self.draft, self.draft), document(entry('bad', 'Bad', '悪', 'unknown'))]:
            with self.assertRaises(ValueError):
                terms.rules(doc)
        with self.assertRaises(ValueError):
            terms.check({}, {}, self.doc, {'terminology': {'exceptonsByKey': {}}})

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text('{"a": 1, "a": 2}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                terms.load(path)

    def test_live_terminology_renders_and_covers_all_original_rows(self):
        live = terms.load(terms.DEFAULT_TERMINOLOGY)
        self.assertEqual(sum(len(s.get('entries', [])) for s in live['sections']), 78)
        self.assertIn('Draft', terms.render(live))
        self.assertFalse(terms.check({}, {}, self.doc)['languageApproval'])

    def test_cli_exit_codes_and_input_write_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in [('en', {'a': 'Draft'}), ('ja', {'a': 'ドラフト'}), ('terms', self.doc)]:
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            command = [sys.executable, '-B', str(SCRIPTS / 'check-terminology.py'), str(root / 'en.json'), str(root / 'ja.json'), '--terminology', str(root / 'terms.json')]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            before = (root / 'ja.json').read_bytes()
            self.assertEqual(subprocess.run(command + ['--output', str(root / 'ja.json')], capture_output=True).returncode, 2)
            self.assertEqual((root / 'ja.json').read_bytes(), before)
            (root / 'ja.json').write_text('{"a":"old"}', encoding='utf-8')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
            (root / 'ja.json').write_text('{', encoding='utf-8')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
