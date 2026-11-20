# Resource integrity and checks

## Supported paths

The bundled validator handles strict JSON (flat/nested objects and arrays) and properties bundles decoded as UTF-8, including Unicode escapes and logical line continuations. It uses Node.js built-ins, reads files only and has no package-install step.

For YAML, JSONC, JavaScript/TypeScript resources, XLIFF, PO or another format, use that project's parser and checks. Do not flatten or convert it to JSON as the delivered artifact merely to use this script.

Determine interpolation and message format from the application. File extension alone does not establish whether a string uses i18next, ICU, SAP MessageFormat or a custom formatter.

## Preserve

- Key names, namespace boundaries, nesting, value types, array order and array length.
- Non-string values exactly. Translate only user-visible string values.
- Source English files and unrelated Japanese strings.
- Existing Japanese-only keys unless deletion was requested. With a baseline, the validator checks they were retained unchanged.
- Placeholder spelling, formatting options, escaping mode and occurrence count. Reordering named/numbered variables may be needed for Japanese; preserve positional argument meaning.
- Markup/component tag names, attributes, nesting and links. Text nodes are translatable; attributes are protected unless explicitly documented as translatable.
- Resource references such as $t(common.save), API/enum values, code snippets, file paths, email addresses, URLs and example formulas.
- Meaningful line breaks/tabs and format escapes. Do not indiscriminately normalize whitespace.

For properties, preserve comment/annotation placement, key order and multiline syntax where practical. Inspect the application's encoding and apostrophe/MessageFormat behavior. The validator does not certify every SAPUI5 version's apostrophe rules, comments or encoding configuration.

## Plural and rich-message rules

i18next uses locale-dependent plural resolution. Keep existing key suffixes and context variants; translate their values. Do not remove _one or _other keys or migrate formats as part of localization. An English and Japanese variant may legitimately have the same Japanese wording.

For ICU plural/select/selectordinal or typed number/date/time arguments, use the application's actual formatter/parser. Preserve argument names, selectors, required branches, offsets, number/date skeletons, escaping and # behavior. Do not translate selector keywords. Changes to locale-specific branches need parser-backed evidence and the requested scope.

Do not run a simple brace regex over an ICU message and claim it proves correctness. The bundled validator flags typed/complex messages as requiring external format checking; it deliberately does not certify their brace syntax or branch equivalence.

For unnumbered printf placeholders, argument order is significant. Do not rearrange %s/%d blindly. Numbered placeholders may move while retaining their index and type.

React Trans numeric/component tags can move with their text as needed, but tag balance and pairing must remain intact.

## Validator usage

    node "<skill-dir>/scripts/validate-i18n.mjs" en.json ja.json --json
    node "<skill-dir>/scripts/validate-i18n.mjs" en.json ja.json --baseline original-ja.json --profile translation-profile.json --json
    node "<skill-dir>/scripts/validate-i18n.mjs" i18n_en.properties i18n_ja.properties --json

For JSON, keys in the report are JSON Pointers, e.g. /common/save. The literal key a.b differs from nested /a/b. Properties keys use the same pointer escaping as a single key component.

Profile options used by the validator:

- unchangedKeys: exact pointer paths permitted to keep English.
- unchangedTexts: exact source values intentionally retained, e.g. a product name.

Other profile fields are for the agent. Avoid broad exclusions. Record why a retained string is intentional in the delivery report.

The optional --allow-extra flag accepts target-only keys without a baseline; each is still reported. Prefer a baseline when modifying an existing file.

Exit codes:

- 0: no detected structural errors; warnings may remain.
- 1: detected structural errors.
- 2: invalid input, unsupported file extension or invalid command options.

Read the JSON status as well as the exit code. Status can be needs-review despite exit 0. A file is never declared linguistically approved by this validator.

## What is checked

- JSON syntax and duplicate object keys, or properties parsing and duplicate decoded keys.
- Missing source paths, extra target paths, type changes, array shape and non-string changes.
- Existing target-only content removed or changed compared with --baseline.
- Missing/extra/repeated placeholders: default i18next double braces, simple braces, dollar braces, common printf forms and balanced $t(...) references.
- Markup tokens and tag balance, protected URLs/emails/backtick code, decoded control characters and HTML entities.
- Non-empty English paired with blank Japanese.
- Possible untranslated strings, numeric literal changes and typed/complex messages needing format checks.

## What remains human/agent work

- Correct business meaning, terminology in context, natural Japanese and completeness of semantic conditions.
- Custom interpolation syntax, JSON metadata strings which should not be translated, every rich-text grammar, apostrophe quoting and ICU AST equivalence.
- Link rendering, accessible names, actual pixel width and runtime interpolation.
- Proving the English source did not change during work. Compare its before/after content or hash independently.
- Distinguishing approved product names from accidental English fallbacks. Identical text is a review candidate, not automatically an error.

Compare counts by string path. Count translated, intentionally retained and pending strings from the agent's reviewed inventory; the script's candidate count alone cannot establish translation coverage.
