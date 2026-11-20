# Reuse a project wording library

Use this workflow when the project supplies a wording library or requests extraction, review and reconstruction. Ordinary translation remains supported without a project library. The scripts use Python 3.10+ standard-library modules; extended structural checks use Node.js. No translation API is called.

## Select wording by scope

Consult the project's library manifest and matching application context. Exact English text is useful for finding candidates, but it is not sufficient to approve a Japanese selection in a new context. Preserve competing reference variants and provenance. Never select a variant merely because it occurs most often.

The examples below use the fictional application `example-app`. Its private workspace may store candidate references in `library/candidates.json`, reviewed decisions in `library/reviewed/example-app-decisions.json`, compiled selections in `example-app.json` and key mappings in `example-app-map.json`. These files are supplied by the consuming project, not this package. Do not promote AI review to native-speaker approval.

## Shared existing-JA selections

If the project supplies library/reviewed/shared.json, consult it together with shared-map.json. Selections are copied from existing Japanese and are valid only for their listed application/source-file/key meanings. Applicable application-specific decisions take precedence; deferred contexts are excluded from the shared scope. New files, keys or meanings need a fresh scope review.

The shared catalog is a partial lookup layer, not a complete locale or the single-application mapping schema used by assemble below. Use an eligible shared selection as evidence for an application-specific decision, then compile that application's complete reviewed worklist/mapping. Do not fill missing keys silently or overwrite accepted app conventions. Current shared choices are AI-selected references, not native-speaker approval or compact-layout acceptance. Preserve app-specific business meanings and terminology, then apply the latest compact-UI policy to the final presentation. Do not copy an older polite sentence unchanged solely because it exists in a library. If a style revision is requested, write a separate draft and report its changes; do not silently overwrite the maintained library selections.

## Extract and plan

The commands below run from the project root. Work in a fresh run directory for new translation work. Extraction refreshes generated reference data, not source resources. Review source changes before replacing an existing worklist.

    python -B skills/sap-saas-i18n-en-ja/scripts/wording_pipeline.py extract --project-root . --manifest library/manifest.json --output . --validator skills/sap-saas-i18n-en-ja/scripts/validate-i18n.mjs
    python -B skills/sap-saas-i18n-en-ja/scripts/wording_pipeline.py plan --project-root . --source sources/example-app/en.json --application example-app --library-dir library --output runs/<new-run>/worklist.json

Review each work item in its listed key contexts and write a decision file containing application, exact worklistSha256 and items with entryId, english, japanese, reviewStatus, basis, reviewNote and referenceCandidateIds. Intentional English retention needs retentionReason. A provisional decision needs actual authorization evidence. One English phrase can have distinct selections with disjoint targetKeys. Unreviewed or missing decisions cannot be compiled.

A changed source, reference pool or key context requires a new review; do not update a hash just to bypass a stale-input check. Preserve the history of a reviewed decision when adding or narrowing its scope.

## Compile and assemble

To reconstruct a reviewed application resource into a new output:

    python -B skills/sap-saas-i18n-en-ja/scripts/wording_pipeline.py compile --plan library/reviewed/example-app-worklist.json --decisions library/reviewed/example-app-decisions.json --output-library library/reviewed/example-app.json --output-mapping library/reviewed/example-app-map.json
    python -B skills/sap-saas-i18n-en-ja/scripts/wording_pipeline.py assemble --project-root . --source sources/example-app/en.json --library library/reviewed/example-app.json --mapping library/reviewed/example-app-map.json --output runs/<new-run>/ja.json
    node skills/sap-saas-i18n-en-ja/scripts/validate-i18n.mjs sources/example-app/en.json runs/<new-run>/ja.json --json
    python -B -X utf8 skills/sap-saas-i18n-en-ja/scripts/check-terminology.py sources/example-app/en.json runs/<new-run>/ja.json --application example-app --profile library/profiles/example-app.json --output runs/<new-run>/terminology.json
    python -B skills/sap-saas-i18n-en-ja/scripts/audit-ui-writing.py sources/example-app/en.json runs/<new-run>/ja.json --output runs/<new-run>/ui-audit.json

For another application or changed keys, compile that run's reviewed worklist/decision files and use its own library and mapping. Promote reviewed decisions to the shared library only with their scope and provenance. Assembly uses the selected Japanese data and exact key mapping; it does not invent wording or silently fall back to English.

## Refresh lookup views and test tools

    python -B skills/sap-saas-i18n-en-ja/scripts/render_library.py --project-root . --catalog example-app
    python -B -m unittest discover -s skills/sap-saas-i18n-en-ja/tests -p test_wording_pipeline.py -v
    node --test skills/sap-saas-i18n-en-ja/tests/validate-i18n.test.mjs

The renderer creates reading views only. Maintain terminology in references/terminology.json and scoped wording in the decision JSON, then regenerate their derived views. terminology.md and library/glossary.md are generated from the structured terminology. Keep output resources and review reports in the run folder, outside source dictionaries. The terminology gate is a separate required check; unresolved context warnings and provisional decisions must be reported even when assembly succeeds.

## Propagate changed conventions before reuse

Latest explicit user conventions supersede older wording selections within the same meaning and scope. Before reusing a selection, compare it with the current terminology and role-specific writing policy. The assemble command copies selected Japanese verbatim and does not read the glossary to rewrite values. Its source/library hashes prove input identity, not compatibility with a newer convention.

Update affected maintained decisions, rebuild their compiled catalog/mapping and reading views, and check the resulting text. Do not edit only a compiled file or change hashes to bypass review. Keep raw source pairs and historical runs unchanged. The shared catalog normally copies existing Japanese verbatim; when a later user convention has no matching existing variant, record a conventionOverride (japanese, convention, confirmedBy: user, date, record) on the shared decision instead of editing compiled output. The builder keeps the existing variant as meaning evidence and marks the entry user-convention-applied. Use historical differences as evidence, not automatic failures under a new convention. Until synchronization is complete, assembled output requires current-policy review and is not accepted solely because reconstruction succeeds.
