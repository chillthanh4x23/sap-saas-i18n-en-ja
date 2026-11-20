# Review and delivery for a requester who does not know Japanese

Write review/report files and use the templates in English unless the user requests another language. Chat explanations may follow the requester's language. Japanese application resource values remain Japanese.

## Ask about meaning

Resolve linguistic choices yourself. Explain a meaningful business uncertainty in language the requester understands, with a recommended interpretation and the consequence of alternatives.

Good:

    Does “Post” on this screen mean posting a document to the ERP, or publishing
    content? I recommend the accounting interpretation if the button sends an
    invoice to SAP.

Bad:

    Choose 転記 or 投稿.

Reuse a decision within its application scope. If it affects many keys, ask once for the concept. Do not interrupt progress for every occurrence of Supplier, Verified, available or successfully. Use available context first.

For a stylistic convention, explain your recommendation and mark it proposed. For unresolved business meaning, deliver independent work as a draft and list affected paths as pending; do not hide a guess inside a completed translation.

## Semantic review

Run the read-only check-terminology.py for strict JSON and report its scoped errors, warnings and provisional decisions separately from structural/style checks. Maintain terminology.json and regenerate its reading views. Context warnings require meaning decisions; they are not a request to force one Japanese word everywhere. See terminology-check.md.

Follow ai-review-workflow.md automatically for every translation request. Complete the actual AI review before returning the outcome, even when the automated check has no findings. Review all new/changed strings, all strings of a new complete translation, and reused wording for its current meaning/conventions. Resolve fixable findings and rerun checks as part of the task. The user should receive the resource and concise review status, without managing a separate review system.

Review all new/changed strings by English/Japanese pair and UI role, not just isolated dictionary terms. Check:

- Business entity and action.
- Actor/permissions and obligation.
- Positive/negative state and success/failure.
- Conditions, exceptions, scope and quantities.
- Interpolation and whether a variable's runtime meaning still fits.
- The same wording for the same concept, and distinct wording for different concepts.
- Natural Japanese appropriate for an IT/SAP user.
- Compact noun/action form for the actual element role, including reused library text.
- Japanese display-budget growth against English, using actual UI limits when known and an explicitly labeled estimate otherwise.

For statuses, compare the whole state family: Draft, Pending, Verified, Approved, Rejected, Failed and Cancelled must not collapse into one state.

For security, billing and destructive operations, preserve precisely what is permitted, charged, retained or deleted. Do not invent assurances.

An English back-translation is helpful for key decisions, but it is not an independent quality test. Do not label another pass by the same AI as native-speaker validation.

## UI-style and layout review

The package default is compact Japanese: short noun/action endings for compact controls and concise wording throughout the UI. Message bodies should use concise natural sentences, with です／ます and 〜してください where appropriate. Headings and status badges may remain short nominal phrases. Preserve clarity, negation, conditions, consequences, scope and certainty; a complete message is not a compactness failure.

Review UI-writing audit findings separately from structural validation. Confirm the element role instead of treating a key-name heuristic as a known component. Compare all final reused/changed strings with the current style policy. A scoped existing translation can remain semantically appropriate while requiring a new compact presentation draft.

Without the running application, report pixel width, clipping, wrapping and runtime variables as not tested. A character ratio or display-cell estimate is not screen-fit approval. Do not inflate a test scope from deterministic reconstruction to first-pass translation or UI acceptance.

## Delivery files

Default outputs for a file task:

1. The complete Japanese resource(s) in the requested location.
2. A concise English translation review with material decisions and check status, unless another report language is requested. Use a separate report for a large task; a short chat summary is enough for a small task.

Only include an updated project profile when decisions were actually made or the user requested it. Keep draft and approved entries distinct. Do not clutter every task with empty reports or auxiliary files.

## English report template

    Result: Translation draft complete / Business clarification pending
    Scope: Files and namespaces processed
    Coverage: N in-scope strings = A translated + B intentionally retained + C pending
    Structure: Passed / Errors detected / Checks incomplete
    Semantic and naturalness review: Performed by AI / Not performed
    Compact UI style review: Performed / Unresolved findings (with retained-wording reasons)
    Width comparison: Actual UI measurement / Estimated display cells / Not checked
    Runtime and layout checks: Performed (describe how) / Not performed

    Important decisions:
    Key | English | Japanese | Plain-English meaning | Reason / decision status

    Pending clarification:
    Key / concept group | Business question | Recommendation and impact

    Checks:
    Tool / scope | Actual result | Remaining limitations

Counts must describe actual reviewed scope. Do not count an English fallback as translated. For large files, summarize ordinary changes and include only important examples; attach a complete machine report when useful.

For zero structural errors with ICU warnings, report that no errors were detected within the checked scope and formatter checks remain pending. Do not claim that all checks passed.

The requester can assess whether the proposed meaning matches the application without understanding Japanese. Avoid unsupported numerical confidence scores such as “99% accurate”.


## Historical evidence and current acceptance

A changed approved convention can legitimately make new output differ from an old run. Keep historical outputs frozen unless revision was requested. Record the applicable policy, exact input identity and current output identity. Validate current terminology separately from structure: the existing structural validator does not enforce the glossary. A first-draft acceptance target means the first saved translation must meet the criteria without internal post-save repairs; reconstruction of known reviewed data is not evidence for unseen translation quality. Explicit user-requested revisions must be identified as revisions, not relabeled as the first candidate.
