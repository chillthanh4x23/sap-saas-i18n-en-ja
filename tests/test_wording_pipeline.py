import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/wording_pipeline.py'
spec = importlib.util.spec_from_file_location('wording_pipeline', SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class WordingPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wording-pipeline-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'output'
        self.en_a = {'save': 'Save', 'otherSave': 'Save', 'a.b': 'Label', 'a': {'b': 'Label'}, 'arr': ['Cancel'], 'id': 9007199254740993, 'rate': 1.5, 'flags': [True, None]}
        self.ja_a = {'save': '保存', 'otherSave': '保存', 'a.b': 'ラベル', 'a': {'b': 'ラベル'}, 'arr': ['キャンセル'], 'id': 9007199254740993, 'rate': 1.5, 'flags': [True, None], 'legacy': '旧表示'}
        self.en_b = {'save': 'Save', 'posted': 'Posted', 'postedAt': 'Posted', 'bad': 'Upload {{file}}', 'new': 'New untranslated text', 'code': 'API'}
        self.ja_b = {'save': '保存', 'posted': '転記済み', 'postedAt': '転記日時', 'bad': 'アップロード', 'new': 'New untranslated text', 'code': 'API'}
        for name, value in [('a_en.json', self.en_a), ('a_ja.json', self.ja_a), ('b_en.json', self.en_b), ('b_ja.json', self.ja_b)]:
            pipeline.save(self.root/name, value)
        pipeline.save(self.root/'manifest.json', {'pairs': [{'id': 'A', 'application': 'A', 'en': 'a_en.json', 'ja': 'a_ja.json'}, {'id': 'B', 'application': 'B', 'en': 'b_en.json', 'ja': 'b_ja.json'}]})
        self.summary = pipeline.extract(self.root, self.root/'manifest.json', self.out)

    def prepare(self, app='A'):
        source = app.lower() + '_en.json'
        work_file = self.root/'plan.json'
        pipeline.plan(self.root, source, app, self.out/'library', work_file)
        work = pipeline.load(work_file)
        values = {'Save': '保存', 'Label': 'ラベル', 'Cancel': 'キャンセル', 'Upload {{file}}': '{{file}}をアップロード', 'New untranslated text': '新しい未翻訳テキスト', 'API': 'API'}
        decisions = []
        for item in work['items']:
            choices = [('/posted', '転記済み'), ('/postedAt', '転記日時')] if item['english'] == 'Posted' else [(None, values[item['english']])]
            for key, value in choices:
                d = {'entryId': item['entryId'], 'english': item['english'], 'japanese': value, 'reviewStatus': 'ai-reviewed', 'basis': 'fixture-review', 'reviewNote': 'Reviewed fixture meaning in its declared key context.', 'referenceCandidateIds': []}
                if key:
                    d['targetKeys'] = [key]
                if value == item['english']:
                    d['retentionReason'] = 'Intentional API acronym.'
                decisions.append(d)
        decision_file = self.root/'decisions.json'
        pipeline.save(decision_file, {'application': app, 'worklistSha256': pipeline.digest(work_file.read_bytes()), 'items': decisions})
        return work_file, decision_file

    def compile(self, app='A'):
        work, decisions = self.prepare(app)
        lib, mapping = self.root/'reviewed.json', self.root/'mapping.json'
        pipeline.compile_library(work, decisions, lib, mapping)
        return work, decisions, lib, mapping

    def test_deduplication_preserves_all_occurrences_and_unpaired_targets(self):
        self.assertEqual(self.summary['sourceStringOccurrences'], 11)
        self.assertEqual(self.summary['uniqueExactEnglishTexts'], 7)
        self.assertEqual(self.summary['duplicateOccurrencesBeyondFirst'], 4)
        self.assertEqual(self.summary['unpairedTargetStrings'], 1)
        orphan = pipeline.load(self.out/'library/unpaired-target-strings.json')['items'][0]
        self.assertEqual(orphan['key'], '/legacy')

    def test_reference_variants_keep_provenance_instead_of_selecting_a_majority(self):
        entry = next(e for e in pipeline.load(self.out/'library/candidates.json')['entries'] if e['english'] == 'Posted')
        self.assertEqual({c['japanese'] for c in entry['candidates']}, {'転記済み', '転記日時'})
        self.assertEqual(entry['reviewStatus'], 'unreviewed-reference-suggestions')

    def test_broken_placeholder_reference_is_preserved_but_not_usable(self):
        entry = next(e for e in pipeline.load(self.out/'library/candidates.json')['entries'] if e['english'] == 'Upload {{file}}')
        self.assertEqual(entry['candidates'][0]['usableOccurrenceIds'], [])
        self.assertEqual(self.summary['referenceStates']['broken-reference'], 1)

    def test_round_trip_preserves_keys_arrays_metadata_and_source(self):
        _, _, lib, mapping = self.compile()
        before = (self.root/'a_en.json').read_bytes()
        target = self.root/'result.json'
        result = pipeline.assemble(self.root, 'a_en.json', lib, mapping, target)
        translated = pipeline.load(target)
        self.assertEqual(result['filledFromReviewedLibrary'], 5)
        self.assertEqual(translated['save'], '保存')
        self.assertEqual(translated['otherSave'], '保存')
        self.assertEqual(translated['a.b'], 'ラベル')
        self.assertEqual(translated['a']['b'], 'ラベル')
        self.assertEqual(translated['arr'], ['キャンセル'])
        self.assertEqual(translated['id'], 9007199254740993)
        self.assertEqual(translated['rate'], 1.5)
        self.assertEqual(translated['flags'], [True, None])
        self.assertEqual((self.root/'a_en.json').read_bytes(), before)
        self.assertNotIn(b'\r\n', lib.read_bytes())

    def test_same_english_can_have_different_reviewed_meanings_within_one_app(self):
        _, _, lib, mapping = self.compile('B')
        pipeline.assemble(self.root, 'b_en.json', lib, mapping, self.root/'b_result.json')
        result = pipeline.load(self.root/'b_result.json')
        self.assertEqual(result['posted'], '転記済み')
        self.assertEqual(result['postedAt'], '転記日時')
        self.assertEqual(result['bad'], '{{file}}をアップロード')

    def test_missing_or_unreviewed_decisions_do_not_fall_back_to_english(self):
        work, decisions = self.prepare()
        doc = pipeline.load(decisions)
        doc['items'].pop()
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'exact worklist'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')
        work, decisions = self.prepare()
        doc = pipeline.load(decisions)
        doc['items'][0]['reviewStatus'] = 'pending'
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'unreviewed'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_english_or_non_japanese_retention_needs_a_reason(self):
        work, decisions = self.prepare('B')
        doc = pipeline.load(decisions)
        item = next(d for d in doc['items'] if d['english'] == 'API')
        del item['retentionReason']
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'retention reason'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_overlapping_context_decisions_are_rejected(self):
        work, decisions = self.prepare()
        doc = pipeline.load(decisions)
        doc['items'].append(copy.deepcopy(doc['items'][0]))
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_repeated_placeholder_counts_cannot_change_in_review(self):
        self.assertEqual(pipeline.pair_quality('{{x}} and {{x}}', '{{x}}です'), ['placeholder-mismatch'])
        work, decisions = self.prepare('B')
        doc = pipeline.load(decisions)
        next(d for d in doc['items'] if d['english'] == 'Upload {{file}}')['japanese'] = 'アップロード'
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'placeholders'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_broken_reference_cannot_be_cited_as_valid_evidence(self):
        work, decisions = self.prepare('B')
        doc, plan = pipeline.load(decisions), pipeline.load(work)
        item = next(i for i in plan['items'] if i['english'] == 'Upload {{file}}')
        d = next(i for i in doc['items'] if i['english'] == 'Upload {{file}}')
        d['referenceCandidateIds'] = [item['candidates'][0]['candidateId']]
        pipeline.save(decisions, doc)
        with self.assertRaisesRegex(ValueError, 'broken reference'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_changed_source_or_library_requires_rebuilding_mapping(self):
        _, _, lib, mapping = self.compile()
        original = (self.root/'a_en.json').read_bytes()
        updated = copy.deepcopy(self.en_a)
        updated['save'] = 'Save now'
        pipeline.save(self.root/'a_en.json', updated)
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            pipeline.assemble(self.root, 'a_en.json', lib, mapping, self.root/'result.json')
        (self.root/'a_en.json').write_bytes(original)
        lib.write_bytes(lib.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'Library changed'):
            pipeline.assemble(self.root, 'a_en.json', lib, mapping, self.root/'result.json')

    def test_mapping_is_bound_to_file_and_exact_context(self):
        _, _, lib, mapping = self.compile()
        (self.root/'other.json').write_bytes((self.root/'a_en.json').read_bytes())
        with self.assertRaisesRegex(ValueError, 'different source file'):
            pipeline.assemble(self.root, 'other.json', lib, mapping, self.root/'result.json')
        doc = pipeline.load(mapping)
        doc['entries'][0]['parts'] = ['arr', 0]
        pipeline.save(mapping, doc)
        with self.assertRaisesRegex(ValueError, 'association'):
            pipeline.assemble(self.root, 'a_en.json', lib, mapping, self.root/'result.json')

    def test_overwriting_inputs_is_rejected(self):
        work, decisions, lib, mapping = self.compile()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            pipeline.assemble(self.root, 'a_en.json', lib, mapping, self.root/'a_en.json')
        with self.assertRaisesRegex(ValueError, 'distinct'):
            pipeline.compile_library(work, decisions, decisions, self.root/'map.json')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            pipeline.plan(self.root, 'a_en.json', 'A', self.out/'library', self.root/'a_en.json')

    def test_old_decisions_cannot_approve_new_key_contexts_automatically(self):
        work, decisions = self.prepare()
        document = pipeline.load(work)
        document['items'][0]['targetKeys'][0] = '/newContext'
        pipeline.save(work, document)
        with self.assertRaisesRegex(ValueError, 'Worklist changed'):
            pipeline.compile_library(work, decisions, self.root/'lib.json', self.root/'map.json')

    def test_duplicate_keys_non_json_constants_and_scalar_resources_are_rejected(self):
        for content, message in [(' {"x":1,"x":2}', 'Duplicate'), ('{"x":NaN}', 'Non-JSON')]:
            (self.root/'invalid.json').write_text(content, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, message):
                pipeline.load(self.root/'invalid.json')
        pipeline.save(self.root/'scalar.json', 'Save')
        with self.assertRaisesRegex(ValueError, 'object or array'):
            pipeline.resource(self.root/'scalar.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
