#!/usr/bin/env python3
"""Render read-only Markdown views of the project glossary and wording library."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from terminology import load as load_terminology, render as render_terminology


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def cell(value):
    return html.escape(str(value), quote=False).replace('|', '&#124;').replace('\r\n', '\n').replace('\n', '<br>')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def render(project_root, catalog='example-app'):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', catalog):
        raise ValueError('Catalog must be a filename basename using letters, digits, underscores or hyphens')
    root = Path(project_root).resolve()
    lib = root / 'library'
    terminology = root / 'skills/sap-saas-i18n-en-ja/references/terminology.md'
    terminology_data = load_terminology(terminology.with_suffix('.json'))
    write(terminology, render_terminology(terminology_data))
    glossary = '# Project glossary\n\nGenerated reading view. Maintain the [structured terminology](../skills/sap-saas-i18n-en-ja/references/terminology.json), then rerun render_library.py. Application-specific decisions take precedence within their reviewed business context.\n\n'
    write(lib / 'glossary.md', glossary + terminology.read_text(encoding='utf-8').split('\n', 1)[1].lstrip())

    candidates = load(lib / 'candidates.json')
    lines = ['# Reference wording candidates', '',
             'Generated from [candidates.json](candidates.json). These are unapproved reference suggestions; identical EN/JA may be a technical identifier or an unfinished fallback. Provenance is in source-occurrences.jsonl.', '',
             '| English | Japanese reference variants | Scope |', '|---|---|---|']
    for entry in sorted(candidates['entries'], key=lambda e: e['english'].casefold()):
        values = '<br>'.join(cell(c['japanese']) for c in entry['candidates'])
        flags = 'multiple variants; review context' if entry['hasMultipleJapaneseValues'] else 'reference suggestion'
        lines.append(f"| {cell(entry['english'])} | {values} | {flags} |")
    write(lib / 'candidates.md', '\n'.join(lines) + '\n')

    compiled = load(lib / 'reviewed' / f'{catalog}.json')
    lines = [f'# Reviewed {catalog} wording', '',
             f'Generated from [{catalog}.json]({catalog}.json). Scope: listed application/key contexts only. This reading view does not establish independent language approval.', '',
             f'Maintain [{catalog}-decisions.json]({catalog}-decisions.json), compile against [{catalog}-worklist.json]({catalog}-worklist.json), then regenerate this view. Selection status and provenance remain in the decision records.', '',
             '| English | Selected Japanese | Review status | Key contexts |', '|---|---|---|---|']
    for entry in sorted(compiled['entries'], key=lambda e: e['english'].casefold()):
        lines.append(f"| {cell(entry['english'])} | {cell(entry['japanese'])} | {cell(entry['reviewStatus'])} | {len(entry['scope']['reviewedKeys'])} |")
    write(lib / 'reviewed' / f'{catalog}.md', '\n'.join(lines) + '\n')
    return {'candidateGroups': len(candidates['entries']), 'reviewedWordings': len(compiled['entries']), 'generatedViews': 4}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--catalog', default='example-app', help='Private reviewed catalog filename basename, without .json')
    args = parser.parse_args()
    print(json.dumps(render(args.project_root, args.catalog), indent=2))
