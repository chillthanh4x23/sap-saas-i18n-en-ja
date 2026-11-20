import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
spec = importlib.util.spec_from_file_location('library_renderer', PACKAGE / 'scripts/render_library.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class LibraryRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        terms = self.root / 'skills/sap-saas-i18n-en-ja/references'
        terms.mkdir(parents=True)
        shutil.copyfile(PACKAGE / 'references/terminology.json', terms / 'terminology.json')
        self.lib = self.root / 'library'
        (self.lib / 'reviewed').mkdir(parents=True)
        (self.lib / 'candidates.json').write_text(json.dumps({'entries': [{
            'english': 'Save', 'candidates': [{'japanese': '保存'}], 'hasMultipleJapaneseValues': False
        }]}), encoding='utf-8')

    def catalog(self, name):
        data = {'entries': [{'english': 'Save', 'japanese': '保存', 'reviewStatus': 'provisional',
                             'scope': {'reviewedKeys': ['/actions/save']}}]}
        path = self.lib / 'reviewed' / (name + '.json')
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_default_catalog_runs_without_external_project_data(self):
        source = self.catalog('example-app')
        before = source.read_bytes()
        result = renderer.render(self.root)
        self.assertEqual(result, {'candidateGroups': 1, 'reviewedWordings': 1, 'generatedViews': 4})
        self.assertEqual(source.read_bytes(), before)
        self.assertIn('provisional', (self.lib / 'reviewed/example-app.md').read_text(encoding='utf-8'))
        for path in ['glossary.md', 'candidates.md', 'reviewed/example-app.md']:
            self.assertTrue((self.lib / path).is_file())

    def test_cli_selects_a_different_catalog(self):
        self.catalog('demo-catalog')
        result = subprocess.run([sys.executable, '-B', str(PACKAGE / 'scripts/render_library.py'),
                                 '--project-root', str(self.root), '--catalog', 'demo-catalog'],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['reviewedWordings'], 1)
        self.assertTrue((self.lib / 'reviewed/demo-catalog.md').is_file())
        self.assertFalse((self.lib / 'reviewed/example-app.md').exists())

    def test_invalid_catalog_is_rejected_before_any_output_is_written(self):
        for name in ['../other', 'nested/name', 'bad.json', '', 'x\\y']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                renderer.render(self.root, name)
        self.assertFalse((self.lib / 'glossary.md').exists())


if __name__ == '__main__':
    unittest.main()
