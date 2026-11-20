# sap-saas-i18n-en-ja

An AI skill for translating English application text (i18n resource files) into Japanese for SAP-related and B2B SaaS products, and for reviewing existing Japanese translations.

It aims for Japanese that SAP practitioners and Japanese IT users recognise: established SAP terms, compact wording for buttons, labels and headings, and natural polite sentences for messages. The person requesting the translation does not need to read Japanese. The skill asks business questions ("Does *Verified* mean a person checked it, or the system validated it?") rather than asking them to choose between Japanese synonyms.

## What it does

- **Translates or reviews** JSON locale files (including i18next / react-i18next) and SAPUI5 `.properties` bundles, including incremental updates.
- **Keeps the file working.** Keys, placeholders, markup, links and non-string values are preserved and checked.
- **Applies a terminology set** of SAP and SaaS vocabulary, with context rules for words whose Japanese depends on meaning (Item, Submit, Available, Supplier…) and checks for known wrong-sense translations.
- **Checks UI writing style by role:** compact controls, polite message bodies, confirmation questions and an estimated width budget.
- **Requires an AI review step** before any result is returned, and reports what was and was not checked.

## Folder contents

| Path | Contents |
|---|---|
| `SKILL.md` | Main instructions read by the AI assistant |
| `references/` | Terminology (`terminology.json` is the maintained source; `terminology.md` is generated), UI-writing rules, integrity rules, review workflow, sources and versioning |
| `scripts/` | Read-only checkers: structure validator, terminology gate, UI-writing audit, plus library helpers |
| `assets/` | Example project profile for app-specific settings |
| `agents/` | Agent metadata |
| `tests/` | Python and Node tests using synthetic data |

## Requirements

- Python 3.10 or later (standard library only)
- Node.js 18 or later for the structure validator (built-in modules only, no package install)

## Use as a skill

Install or copy this folder into your assistant's skills directory, then ask for a translation, for example:

> Translate `en.json` into Japanese for SAP users and review the result.

The assistant follows `SKILL.md`: it translates, runs the checks below, reviews the result in context, fixes real issues and reports any open questions.

## Run the checks yourself

All checks are read-only; they never change your files.

```text
# 1. Structure: keys, placeholders, markup, English fallbacks
node scripts/validate-i18n.mjs en.json ja.json --json

# 2. Terminology rules (strict JSON)
python -B -X utf8 scripts/check-terminology.py en.json ja.json --output terminology-report.json

# 3. UI-writing style and estimated width (strict JSON)
python -B scripts/audit-ui-writing.py en.json ja.json --output ui-audit.json
```

Each command also accepts `--profile <project-profile.json>` for app-specific decisions and roles. See `assets/project-profile.example.json`.

## Project-specific settings stay with your project

Keep your own app's conventions, profiles, source files and translation runs in your own private project, not in this folder. A wording decision for one application is not a rule for every application. See `references/public-distribution.md`.

## Limits

- The review is done by AI. It is not approval by a native Japanese speaker.
- The width check is an estimate. Layout on the real screen, runtime formatting and ICU/MessageFormat messages need testing in the application.
- A passing check shows that the file is consistent within the checker's scope, not that every translation is correct.

## Tests

```text
python -B -X utf8 -m unittest discover -s tests -p "test_*.py"
node --test tests/validate-i18n.test.mjs
```

## Version

See `VERSION` and `CHANGELOG.md`. Releases follow [Semantic Versioning](https://semver.org/) and are tagged `vX.Y.Z`.

## License and credits

Released under the MIT License (see `LICENSE`).

Some writing principles are adapted from [coji/natural-japanese](https://github.com/coji/natural-japanese) (MIT). Its notice is kept in `THIRD_PARTY_NOTICES.txt`.
