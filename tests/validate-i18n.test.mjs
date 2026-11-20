import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { validateFiles } from '../scripts/validate-i18n.mjs';

const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'i18n-draft-tests-'));
const script = fileURLToPath(new URL('../scripts/validate-i18n.mjs', import.meta.url));
let serial = 0;
after(() => {
  const resolved = path.resolve(directory);
  if (path.dirname(resolved) !== path.resolve(os.tmpdir()) || !path.basename(resolved).startsWith('i18n-draft-tests-')) throw new Error('Unexpected temporary cleanup path');
  fs.rmSync(resolved, { recursive: true, force: true });
});
function file(content, extension = 'json', raw = false) {
  const filename = path.join(directory, `${serial++}.${extension}`);
  fs.writeFileSync(filename, raw ? content : JSON.stringify(content), 'utf8');
  return filename;
}
function run(en, ja, options = {}) { return validateFiles(file(en), file(ja), options); }
const codes = result => result.issues.map(i => i.code);

test('valid nested Japanese preserves metadata, arrays and repeated placeholders', () => {
  const result = run({ a: { save: 'Save', message: '{{name}} selected {{name}}' }, list: ['Cancel'], flag: true, n: 5, x: null },
    { a: { save: '保存', message: '{{name}}が{{name}}を選択しました' }, list: ['キャンセル'], flag: true, n: 5, x: null });
  assert.equal(result.counts.errors, 0);
  assert.equal(result.counts.warnings, 0);
  assert.equal(result.languageApproval, false);
});
test('missing and extra keys, type changes and non-string mutations fail', () => {
  const result = run({ a: 'Save', list: ['Cancel'], n: 3, flag: true }, { x: '保存', list: 'キャンセル', n: 4, flag: false });
  for (const code of ['missing-key', 'extra-key', 'type-mismatch', 'non-string-change']) assert.ok(codes(result).includes(code), code);
});
test('array length change fails even if extra keys are permitted', () => {
  assert.ok(codes(run({ a: ['Save'] }, { a: ['保存', '追加'] }, { allowExtra: true })).includes('array-length'));
});
test('numeric metadata cannot change unnoticed through JavaScript rounding', () => {
  const source = file('{"label":"Save","n":9007199254740993}', 'json', true);
  const target = file('{"label":"保存","n":9007199254740992}', 'json', true);
  assert.ok(codes(validateFiles(source, target)).includes('non-string-change'));
});
test('duplicate escaped JSON keys are detected before information loss is hidden', () => {
  const result = validateFiles(file({ save: 'Save' }), file('{"save":"保存","\\u0073ave":"登録"}', 'json', true));
  assert.ok(codes(result).includes('duplicate-key'));
});
test('literal dotted keys, nested keys and pointer escapes stay distinct', () => {
  const result = run({ 'a.b': 'Save', a: { b: 'Cancel' }, 'a/b~c': 'Close' }, { 'a.b': '保存', a: { b: 'キャンセル' }, 'a/b~c': '閉じる' });
  assert.equal(result.counts.errors, 0);
  const missing = run({ 'a.b': 'Save', a: { b: 'Cancel' } }, { 'a.b': '保存' });
  assert.ok(missing.issues.some(i => i.key === '/a/b' && i.code === 'missing-key'));
});
test('missing repeated or added placeholders and changed escaping mode fail', () => {
  for (const [en, ja] of [['{{name}} and {{name}}', '{{name}}です'], ['Save {0}', '{0}と{1}を保存'], ['{{- html}}', '{{html}}']]) {
    assert.ok(codes(run({ x: en }, { x: ja })).includes('placeholder-mismatch'));
  }
});
test('numbered placeholders may move while unnumbered printf types keep order', () => {
  assert.equal(run({ x: '%1$s has %2$d records' }, { x: '%2$d件のレコードを%1$sが保持しています' }).counts.errors, 0);
  assert.ok(codes(run({ x: '%s has %d records' }, { x: '%d件を%sが保持しています' })).includes('printf-order'));
  assert.equal(run({ x: '{0} and ${value}' }, { x: '${value}と{0}' }).counts.errors, 0);
});
test('rich text, URLs, control characters and nested references are protected', () => {
  const en = { x: '<1>Save</1>\n$t(common.save)', url: 'See https://example.test/help', tabs: 'A\tB' };
  const ja = { x: '<1>保存</1>\n$t(common.save)', url: 'https://example.test/helpを参照', tabs: '甲\t乙' };
  assert.equal(run(en, ja).counts.errors, 0);
  const broken = run(en, { ...ja, x: '<1>保存</2> $t(common.cancel)', url: 'https://evil.test/helpを参照', tabs: '甲乙' });
  for (const code of ['markup-mismatch', 'unbalanced-markup', 'nested-reference-mismatch', 'protected-literal-mismatch', 'control-character-mismatch']) assert.ok(codes(broken).includes(code), code);
});
test('tag order cannot turn balanced tags into crossing tags', () => {
  assert.ok(codes(run({ x: '<b><i>Save</i></b>' }, { x: '<b><i>保存</b></i>' })).includes('unbalanced-markup'));
});
test('blank translations fail; English fallbacks are reviewed rather than counted as translated', () => {
  assert.ok(codes(run({ x: 'Save' }, { x: ' ' })).includes('blank-target'));
  const result = run({ x: 'Agent Tools Configuration' }, { x: 'Agent Tools Configuration' });
  assert.equal(result.status, 'needs-review');
  assert.ok(codes(result).includes('unchanged-english'));
  assert.equal(result.languageApproval, false);
});
test('explicit unchanged names are allowed without globally ignoring English', () => {
  const result = run({ title: 'ExampleApp', help: 'Agent Tools Configuration' }, { title: 'ExampleApp', help: 'Agent Tools Configuration' }, { profile: { unchangedKeys: ['/title'], unchangedTexts: [] } });
  assert.equal(result.issues.filter(i => i.code === 'unchanged-english').length, 1);
  assert.equal(result.issues.find(i => i.code === 'unchanged-english').key, '/help');
});
test('baseline target-only paths are preserved, and deletion or mutation fails', () => {
  const baseline = file({ save: '保存', legacy: { old: '旧画面' } });
  assert.equal(run({ save: 'Save' }, { save: '保存', legacy: { old: '旧画面' } }, { baseline }).counts.errors, 0);
  assert.ok(codes(run({ save: 'Save' }, { save: '保存' }, { baseline })).includes('baseline-extra-removed'));
  assert.ok(codes(run({ save: 'Save' }, { save: '保存', legacy: { old: '変更' } }, { baseline })).includes('baseline-extra-changed'));
});
test('ICU is explicitly incomplete even with no detected structural errors', () => {
  const result = run({ x: '{count, plural, one {One file} other {# files}}' }, { x: '{count, plural, one {1件のファイル} other {#件のファイル}}' });
  assert.equal(result.counts.errors, 0);
  assert.equal(result.status, 'needs-review');
  assert.ok(codes(result).includes('external-format-check-required'));
});
test('JSON parse errors and unsupported formats are rejected', () => {
  assert.throws(() => validateFiles(file('{', 'json', true), file({ x: '保存' })), SyntaxError);
  assert.throws(() => validateFiles(file('x: Save', 'yaml', true), file({ x: '保存' })), /Unsupported/);
});
test('properties support escaped delimiters, continuations and Unicode escapes', () => {
  const en = file('# comment\nsave\\ key=Save {0}\nlong=Upload \\\n  {0}\nname=Name\n', 'properties', true);
  const ja = file('# comment\nsave\\ key=保存 {0}\nlong={0}をアップロード\nname=\\u540d\\u524d\n', 'properties', true);
  const result = validateFiles(en, ja);
  assert.equal(result.counts.sourceStrings, 3);
  assert.equal(result.counts.errors, 0);
});
test('properties duplicate decoded keys and invalid escapes are caught', () => {
  const en = file('save=Save\n', 'properties', true);
  const dup = file('save=保存\n\\u0073ave=登録\n', 'properties', true);
  assert.ok(codes(validateFiles(en, dup)).includes('duplicate-key'));
  assert.throws(() => validateFiles(en, file('save=\\uZZZZ\n', 'properties', true)), /Unicode/);
});
test('validator does not modify source or target', () => {
  const en = file({ x: 'Save {{name}}' }); const ja = file({ x: '{{name}}を保存' });
  const before = [fs.readFileSync(en), fs.readFileSync(ja)];
  validateFiles(en, ja);
  assert.deepEqual(fs.readFileSync(en), before[0]); assert.deepEqual(fs.readFileSync(ja), before[1]);
});
test('CLI distinguishes structural errors, invalid input and warning-only results', () => {
  const en = file({ x: 'Save' });
  for (const [target, expected] of [[file({ x: '保存' }), 0], [file({ x: '' }), 1], [file('{', 'json', true), 2]]) {
    const result = spawnSync(process.execPath, [script, en, target, '--json'], { encoding: 'utf8' });
    assert.equal(result.status, expected, result.stdout + result.stderr);
    assert.ok(JSON.parse(result.stdout).status);
  }
  const warning = spawnSync(process.execPath, [script, en, file({ x: 'Save' }), '--json'], { encoding: 'utf8' });
  assert.equal(warning.status, 0); assert.equal(JSON.parse(warning.stdout).status, 'needs-review');
});
