# Current terminology check

## Maintained source

Maintain `terminology.json`. It contains the 78 glossary rows, context guidance and 44 deliberately scoped executable rules. `terminology.md` and the project's `library/glossary.md` are generated reading views. Edit neither reading view directly. Unchecked rows remain guidance; a glossary suggestion is not automatically a required Japanese spelling.

From this project root, regenerate the reading views with:

    python -B -X utf8 skills/sap-saas-i18n-en-ja/scripts/render_library.py --project-root . --catalog example-app

For a standalone copy of the skill, without a project library:

    python -B -X utf8 <skill-dir>/scripts/terminology.py --output <skill-dir>/references/terminology.md

## Run after structural validation

    python -B -X utf8 skills/sap-saas-i18n-en-ja/scripts/check-terminology.py <en.json> <ja.json> --profile <profile.json> --application <app> --output <new-run>/terminology.json

The checker uses Python 3.10+ standard-library modules and strict UTF-8 JSON. The terminology path defaults to this skill's `references/terminology.json`; `--terminology` can select another structured glossary. A profile is optional. Its `application`, if supplied, must agree with `--application`. Reports include input hashes. The checker never repairs translations and refuses to write its report over an input.

## Rule meanings

- **Required:** error-level Draft / Drafts requires ドラフト in visible text, including compounds, and rejects 下書き for that concept. Other required checks are warning-level exact-label suggestions. They are not universal terminology bans.
- **Deprecated:** reports マスターデータ for Master Data as a warning-level package convention. Vector remains vocabulary guidance without an application-specific executable rule; use a private terminology file for additional scoped rules.
- **Context-dependent:** asks for the business sense of terms such as Item, Verified, Supplier Invoice and Document Type. It never selects one Japanese translation from the alternatives. In particular, an ERP 伝票タイプ is not automatically changed to ドキュメントタイプ.

English matching is case-insensitive, uses word boundaries, and prefers the longest non-overlapping phrase. Invoice Date therefore does not separately require Invoice. Exact-label rules apply only to the complete visible label; they do not search every sentence for every suggested glossary word.

Placeholders, common paths/filenames, links, markup attributes, backtick code and resource references are masked. Visible text inside markup remains checked. JSON object/array examples are skipped and reported. Typed/complex formatting is reported for parser-backed review. These masks are conservative, not a complete parser for ICU, custom interpolation or every code language. Explicit technical records are available for ambiguous identifiers; resource keys and non-string values are never checked as prose.

## Scoped decisions and exceptions

Optional profile fields live under `terminology`. Keys are JSON Pointers. Each key maps to a list because one string may contain multiple concepts. All records bind the exact complete source and target plus a reason; changing either text invalidates them. Keep decisions within their application, source version and business meaning.

```json
{
  "application": "ExampleApp",
  "terminology": {
    "decisionsByKey": {
      "/invoice/item": [{
        "termId": "item",
        "source": "Item",
        "target": "明細",
        "meaning": "A document line item",
        "reason": "This label heads the invoice line-item table.",
        "status": "provisional"
      }]
    },
    "exceptionsByKey": {},
    "technicalByKey": {}
  }
}
```

`decisionsByKey` resolves context rules only. Use `status: provisional` for a temporary decision awaiting confirmation, `ai-reviewed` for an actual contextual AI review, and `confirmed` only with actual confirmation evidence in the reason. An ai-reviewed record additionally requires `reviewedBy` (the actual reviewer name) and a nonempty `evidence` list of specific contextual facts or references. AI-reviewed and provisional counts are reported separately; neither implies independent Japanese-speaker approval. A run whose only unresolved status is provisional context choices is reported as `passed-with-provisional-decisions`.

An `exceptionsByKey` record needs `termId`, exact `source` and `target`, `reason`, and specific `codes`: `required-term-missing`, `deprecated-term` or `context-decision-needed`. It retains that finding with a reason; it does not suppress other concepts/codes or extend to changed text. A `technicalByKey` record needs exact `source`, `target` and `reason`, and skips that whole technical string. Do not use broad exclusions or create exceptions merely to make a run pass.

## Status and exit codes

| Exit | Meaning |
|---|---|
| 0 | No open findings in the implemented scope; provisional decisions, if any, are disclosed. |
| 1 | Required-rule errors, review warnings or an incomplete source/target pair. Inspect `status`, `counts` and individual findings. Context warnings are questions to review, not proven mistranslations. |
| 2 | Invalid inputs/settings or an unwritable report. No valid new report is claimed. |

After any translation or active-catalog assembly, run structure, terminology and UI-style checks separately. Do not call the result accepted while terminology findings are unresolved; report errors, context review and authorized provisional choices separately. Do not rewrite a frozen historical resource just because current terminology flags it. These checks do not establish complete glossary compliance, business-meaning correctness, independent Japanese-speaker approval or actual rendered fit.

The translating assistant must perform the [AI review before the outcome](ai-review-workflow.md), including applicable glossary guidance beyond executable rules. It runs the tools and resolves findings as part of the user's translation request. The requester does not need to run these commands or fill profile records. The checker itself remains a local checker and does not invoke a separate AI service.
