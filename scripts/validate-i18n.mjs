#!/usr/bin/env node
// Read-only structural QA. Does not translate, repair, or certify Japanese quality.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ptr = (base, key) => `${base}/${String(key).replace(/~/g, '~0').replace(/\//g, '~1')}`;
const kind = v => v === null ? 'null' : Array.isArray(v) ? 'array' : typeof v;
const issue = (severity, code, key, message, detail = {}) => ({ severity, code, key, message, ...detail });
const multiset = values => [...values.reduce((m, s) => m.set(s, (m.get(s) || 0) + 1), new Map())].sort(([a], [b]) => a.localeCompare(b));
const sameBag = (a, b) => JSON.stringify(multiset(a)) === JSON.stringify(multiset(b));
const readUtf8 = filename => new TextDecoder('utf-8', { fatal: true }).decode(fs.readFileSync(filename)).replace(/^\uFEFF/, '');

// JSON.parse first enforces grammar; this second traversal detects keys it would overwrite.
function inspectJsonSyntax(text) {
  let i = 0;
  const duplicates = [];
  const numericLiterals = new Map();
  const ws = () => { while (/\s/.test(text[i] || '') && i < text.length) i++; };
  const string = () => {
    const start = i++;
    while (i < text.length) {
      if (text[i] === '\\') { i += 2; continue; }
      if (text[i++] === '"') break;
    }
    return JSON.parse(text.slice(start, i));
  };
  function value(base) {
    ws();
    if (text[i] === '{') {
      i++; ws(); const seen = new Set();
      if (text[i] === '}') { i++; return; }
      while (i < text.length) {
        ws(); const key = string(); ws(); i++;
        const child = ptr(base, key);
        if (seen.has(key)) duplicates.push(child);
        seen.add(key); value(child); ws();
        if (text[i++] === '}') break;
      }
    } else if (text[i] === '[') {
      i++; ws(); let index = 0;
      if (text[i] === ']') { i++; return; }
      while (i < text.length) {
        value(ptr(base, index++)); ws();
        if (text[i++] === ']') break;
      }
    } else if (text[i] === '"') string();
    else {
      const start = i;
      while (i < text.length && !/[\s,}\]]/.test(text[i])) i++;
      const literal = text.slice(start, i);
      if (/^-?\d/.test(literal)) numericLiterals.set(base, literal);
    }
  }
  value(''); return { duplicates, numericLiterals };
}

function nodesFrom(value, base = '', nodes = new Map()) {
  const type = kind(value);
  nodes.set(base, { type, value: type === 'array' || type === 'object' ? undefined : value, length: type === 'array' ? value.length : undefined });
  if (type === 'array' || type === 'object') {
    for (const [key, child] of Object.entries(value)) nodesFrom(child, ptr(base, key), nodes);
  }
  return nodes;
}

function unescapeProperties(s) {
  return s.replace(/\\(u[0-9a-fA-F]{4}|[\s\S])/g, (_, token) => {
    if (token[0] === 'u') {
      if (!/^u[0-9a-fA-F]{4}$/.test(token)) throw new Error('Invalid properties Unicode escape');
      return String.fromCharCode(parseInt(token.slice(1), 16));
    }
    return ({ t: '\t', r: '\r', n: '\n', f: '\f' })[token] ?? token;
  });
}
function properties(text) {
  const entries = new Map(); const duplicates = [];
  let logical = ''; let continuing = false;
  function add(line) {
    line = line.replace(/^[ \t\f]+/, '');
    if (!line || /^[#!]/.test(line)) return;
    let end = 0;
    while (end < line.length) {
      if (line[end] === '\\') { end += 2; continue; }
      if (/[=: \t\f]/.test(line[end])) break;
      end++;
    }
    let start = end;
    while (/[ \t\f]/.test(line[start] || '') && start < line.length) start++;
    if (line[start] === '=' || line[start] === ':') start++;
    while (/[ \t\f]/.test(line[start] || '') && start < line.length) start++;
    const rawKey = line.slice(0, end); const rawValue = line.slice(start);
    // Java-style properties permit escaped delimiters and literal backslashes.
    for (const part of [rawKey, rawValue]) {
      for (let j = 0; j < part.length; j++) {
        if (part[j] !== '\\') continue;
        if (part[j + 1] === 'u' && !/^[0-9a-fA-F]{4}$/.test(part.slice(j + 2, j + 6))) throw new Error('Invalid properties Unicode escape');
        j += part[j + 1] === 'u' ? 5 : 1;
      }
    }
    const key = unescapeProperties(rawKey);
    if (entries.has(key)) duplicates.push(ptr('', key));
    entries.set(key, unescapeProperties(rawValue));
  }
  for (const physical of text.split(/\r\n|\n|\r/)) {
    if (!continuing && /^[ \t\f]*(?:[#!]|$)/.test(physical)) continue;
    const next = continuing ? physical.replace(/^[ \t\f]+/, '') : physical;
    logical += next;
    const slashes = logical.match(/\\+$/)?.[0].length || 0;
    continuing = slashes % 2 === 1;
    if (continuing) logical = logical.slice(0, -1);
    else { add(logical); logical = ''; }
  }
  if (continuing) throw new Error('Unfinished properties continuation');
  const nodes = new Map([['', { type: 'object' }]]);
  for (const [key, value] of entries) nodes.set(ptr('', key), { type: 'string', value });
  return { nodes, duplicates };
}

export function loadResource(filename) {
  const text = readUtf8(filename);
  const ext = path.extname(filename).toLowerCase();
  if (ext === '.properties') return { ...properties(text), format: 'properties' };
  if (ext !== '.json') throw new Error(`Unsupported resource extension: ${ext}`);
  const value = JSON.parse(text);
  if (value === null || typeof value !== 'object') throw new Error('JSON resource must be an object or array');
  const syntax = inspectJsonSyntax(text);
  const nodes = nodesFrom(value);
  for (const [key, literal] of syntax.numericLiterals) nodes.get(key).literal = literal;
  return { nodes, duplicates: syntax.duplicates, format: 'json' };
}

function nestedReferences(s) {
  const result = []; let start = 0; let malformed = false;
  while ((start = s.indexOf('$t(', start)) !== -1) {
    let depth = 1; let quote = ''; let i = start + 3;
    for (; i < s.length && depth; i++) {
      const c = s[i];
      if (c === '\\') { i++; continue; }
      if (quote) { if (c === quote) quote = ''; continue; }
      if (c === '"' || c === "'") { quote = c; continue; }
      if (c === '(') depth++;
      if (c === ')') depth--;
    }
    result.push(s.slice(start, i));
    if (depth) malformed = true;
    start = i;
  }
  return { tokens: result, malformed };
}
const printfRegex = /%(?:\d+\$)?[-+0#]*(?:\d+|\*(?:\d+\$)?)?(?:\.(?:\d+|\*(?:\d+\$)?))?[hlLzjt]*[diuoxXfFeEgGaAcspn%]/g;
const typedMessage = s => /\{[\w.-]+\s*,\s*[A-Za-z]+\s*[,}]/.test(s);
function placeholders(s, skipBraces) {
  const result = [];
  const braces = /\{\{[^{}]*\}\}|\$\{[^{}]*\}|\{[\w.-]+\}/g;
  for (const match of s.matchAll(braces)) {
    if (skipBraces && !match[0].startsWith('{{') && !match[0].startsWith('${')) continue;
    result.push(match[0]);
  }
  return result;
}
function tags(s) {
  const tokens = s.match(/<\/?(?:[A-Za-z][\w:.-]*|\d+)(?:\s+(?:[^>"']|"[^"]*"|'[^']*')*)?\s*\/?>/g) || [];
  const stack = []; let balanced = true;
  const voids = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
  for (const token of tokens) {
    const name = token.match(/^<\/?([^\s/>]+)/)[1];
    if (token.startsWith('</')) { if (stack.pop() !== name) balanced = false; }
    else if (!token.endsWith('/>') && !voids.has(name.toLowerCase())) stack.push(name);
  }
  return { tokens, balanced: balanced && !stack.length };
}
const protectedLiterals = s => s.match(/https?:\/\/[A-Za-z0-9\-._~:/?#[\]@!$&'()*+,;=%]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|`[^`\r\n]+`/g)?.map(x => x.replace(/[.,;!?]+$/, '')) || [];
const controls = s => s.match(/\r\n|\r|\n|\t|\f/g) || [];
const entities = s => s.match(/&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);/g) || [];
const numbers = s => s.normalize('NFKC').match(/\d+(?:[.,]\d+)*/g) || [];
const japanese = s => /[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u.test(s);
const retainedToken = s => /^(?:SAP|SaaS|ERP|API|CSV|JSON|XML|URL|URI|ID|UUID|HTTP|HTTPS|OAuth(?: ?2(?:\.0)?)?|SAML|OData|SSO|OK|N\/A|PDF|Excel|px)$/i.test(s.trim()) || !/[A-Za-z]/.test(s);

function checkString(en, ja, key, profile) {
  const issues = [];
  const add = (severity, code, message, detail) => issues.push(issue(severity, code, key, message, detail));
  if (en.trim() && !ja.trim()) add('error', 'blank-target', 'Non-empty source has a blank target.');
  const typed = typedMessage(en) || typedMessage(ja);
  if (typed) add('warning', 'external-format-check-required', 'Typed/complex message detected. Check with the application formatter/parser; brace and branch syntax is not certified here.');
  const enRefs = nestedReferences(en); const jaRefs = nestedReferences(ja);
  if (enRefs.malformed || jaRefs.malformed) add('error', 'malformed-nested-reference', 'Unbalanced $t(...) reference detected.');
  if (!sameBag(enRefs.tokens, jaRefs.tokens)) add('error', 'nested-reference-mismatch', 'Nested translation references changed.');
  const ePH = placeholders(en, typed); const jPH = placeholders(ja, typed);
  if (!sameBag(ePH, jPH)) add('error', 'placeholder-mismatch', 'Placeholder spelling or occurrence counts changed.', { sourceTokens: ePH, targetTokens: jPH });
  const ePrint = en.match(printfRegex) || []; const jPrint = ja.match(printfRegex) || [];
  if (!sameBag(ePrint, jPrint)) add('error', 'printf-mismatch', 'Printf argument tokens changed.');
  const positional = p => !/^%\d+\$/.test(p) && p !== '%%';
  if (JSON.stringify(ePrint.filter(positional)) !== JSON.stringify(jPrint.filter(positional))) add('error', 'printf-order', 'Unnumbered printf arguments changed order.');
  if ([...ePrint, ...jPrint].some(p => p.includes('*'))) add('warning', 'printf-width-review', 'Dynamic printf width/precision needs a runtime argument-order check.');
  const eTags = tags(en); const jTags = tags(ja);
  if (!sameBag(eTags.tokens, jTags.tokens)) add('error', 'markup-mismatch', 'Markup tags or protected attributes changed.');
  if (!eTags.balanced) add('warning', 'source-markup-review', 'Source contains unbalanced tag-like text. Confirm whether it is markup or a literal example.');
  if (eTags.balanced && !jTags.balanced) add('error', 'unbalanced-markup', 'Target markup nesting is not balanced.');
  if (!sameBag(protectedLiterals(en), protectedLiterals(ja))) add('error', 'protected-literal-mismatch', 'URL, email or backtick code changed.');
  if (!sameBag(controls(en), controls(ja))) add('error', 'control-character-mismatch', 'Decoded line breaks, tabs or control characters changed.');
  if (!sameBag(entities(en), entities(ja))) add('error', 'html-entity-mismatch', 'HTML entity tokens changed.');
  if (!sameBag(numbers(en), numbers(ja))) add('warning', 'numeric-literal-review', 'Numeric literals differ. Confirm quantities, dates, thresholds and formats.');
  const allowed = profile.unchangedKeys.includes(key) || profile.unchangedTexts.includes(en) || retainedToken(en);
  if (en.trim() && en === ja && !allowed) add('warning', 'unchanged-english', 'Source and target are identical; classify as intentional retention or unfinished translation.');
  else if (ja.trim() && !japanese(ja) && /[A-Za-z]{2}/.test(ja) && !allowed && !retainedToken(ja)) add('warning', 'no-japanese-review', 'Target contains no Japanese script; confirm that the entire string is intentionally retained.');
  return issues;
}

export function validateFiles(sourceFile, targetFile, options = {}) {
  const source = loadResource(sourceFile); const target = loadResource(targetFile);
  const baseline = options.baseline ? loadResource(options.baseline) : null;
  if (source.format !== target.format || (baseline && baseline.format !== target.format)) throw new Error('Source, target and baseline formats must match');
  const profile = { unchangedKeys: [], unchangedTexts: [], ...options.profile };
  for (const field of ['unchangedKeys', 'unchangedTexts']) {
    if (!Array.isArray(profile[field]) || profile[field].some(v => typeof v !== 'string')) throw new Error(`Profile ${field} must be an array of strings`);
  }
  const issues = [];
  for (const [label, resource] of [['source', source], ['target', target], ['baseline', baseline]]) {
    if (resource) for (const key of resource.duplicates) issues.push(issue('error', 'duplicate-key', key, `Duplicate key in ${label} resource.`));
  }
  let comparedStrings = 0; let missingStrings = 0;
  for (const [key, en] of source.nodes) {
    const ja = target.nodes.get(key);
    if (!ja) {
      issues.push(issue('error', 'missing-key', key, 'Source path is absent from target.'));
      if (en.type === 'string') missingStrings++;
      continue;
    }
    if (en.type !== ja.type) { issues.push(issue('error', 'type-mismatch', key, `Expected ${en.type}, found ${ja.type}.`)); continue; }
    if (en.type === 'array' && en.length !== ja.length) issues.push(issue('error', 'array-length', key, 'Array length changed.'));
    if (en.type === 'string') { comparedStrings++; issues.push(...checkString(en.value, ja.value, key, profile)); }
    else if (!['object', 'array'].includes(en.type) && (!Object.is(en.value, ja.value) || en.literal !== ja.literal)) issues.push(issue('error', 'non-string-change', key, 'Non-string value or numeric representation changed.'));
  }
  let extraPaths = 0;
  for (const [key] of target.nodes) {
    if (source.nodes.has(key)) continue;
    extraPaths++;
    if (baseline?.nodes.has(key)) continue;
    // One finding per highest extra subtree, with exact total in counts.
    if (!source.nodes.has(key.slice(0, key.lastIndexOf('/')))) continue;
    issues.push(issue(options.allowExtra ? 'warning' : 'error', 'extra-key', key, 'Target-only path has no preserved baseline.'));
  }
  if (baseline) for (const [key, before] of baseline.nodes) {
    if (source.nodes.has(key)) continue;
    const after = target.nodes.get(key);
    if (!after) issues.push(issue('error', 'baseline-extra-removed', key, 'Existing target-only content was removed.'));
    else if (before.type !== after.type || before.value !== after.value || before.length !== after.length || before.literal !== after.literal) issues.push(issue('error', 'baseline-extra-changed', key, 'Existing target-only content changed.'));
  }
  const errors = issues.filter(i => i.severity === 'error').length;
  const warnings = issues.filter(i => i.severity === 'warning').length;
  return {
    status: errors ? 'errors' : warnings ? 'needs-review' : 'no-detected-structural-issues',
    source: path.resolve(sourceFile), target: path.resolve(targetFile), format: source.format,
    counts: { sourceStrings: [...source.nodes.values()].filter(v => v.type === 'string').length, targetStrings: [...target.nodes.values()].filter(v => v.type === 'string').length, comparedStrings, missingStrings, extraPaths, errors, warnings },
    languageApproval: false,
    limitations: ['No business-meaning, terminology or Japanese-language certification.', 'ICU/typed messages, custom interpolation and application rendering need separate checks.', 'Comments, formatting layout and source-file immutability need separate review.'],
    issues
  };
}

function main(args) {
  if (args.includes('--help') || !args.length) {
    console.log('Usage: node validate-i18n.mjs source.(json|properties) target.(json|properties) [--baseline original-ja] [--profile profile.json] [--allow-extra] [--json]');
    return 0;
  }
  const positional = []; const options = {}; let json = false;
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--json') json = true;
    else if (a === '--allow-extra') options.allowExtra = true;
    else if (a === '--baseline' || a === '--profile') {
      const v = args[++i]; if (!v || v.startsWith('--')) throw new Error(`Missing value for ${a}`);
      if (a === '--baseline') options.baseline = v;
      else options.profile = JSON.parse(readUtf8(v));
    } else if (a.startsWith('--')) throw new Error(`Unknown option: ${a}`);
    else positional.push(a);
  }
  if (positional.length !== 2) throw new Error('Provide exactly one source and one target resource');
  const result = validateFiles(...positional, options);
  if (json) console.log(JSON.stringify(result, null, 2));
  else {
    console.log(`${result.status}: ${result.counts.errors} error(s), ${result.counts.warnings} warning(s); ${result.counts.comparedStrings}/${result.counts.sourceStrings} source strings compared.`);
    for (const item of result.issues) console.log(`${item.severity.toUpperCase()} ${item.key || '/'} [${item.code}] ${item.message}`);
    console.log('This result is structural QA only; it is not Japanese-language approval.');
  }
  return result.counts.errors ? 1 : 0;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) {
    console.log(JSON.stringify({ status: 'invalid-input', languageApproval: false, message: error.message }));
    process.exitCode = 2;
  }
}
