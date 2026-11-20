# Automatic terminology check and AI review

Apply this process whenever the user asks to translate a file. The assistant performs all steps as part of the task. The user supplies the translation request and application facts; they do not manage review files, run commands or choose Japanese synonyms.

## Before translating

Read the current terminology set (terminology.json and its readable terminology.md), UI-writing policy and matching application decisions. The terminology is working guidance with different evidence levels, not a universally verified dictionary. Identify the business meaning and UI role from the English, namespace and available application context.

Use the same Japanese for the same meaning. When the same English word has different meanings, decide separately for each context: for example, Item may mean an invoice line item, material or field/list entry. Applicable user-confirmed meanings and product conventions take priority. Research matching official product/module terminology when the proposed wording is uncertain or conflicts with the source meaning.

## Before returning the outcome

1. Translate into a working candidate. Keep source resources and historical runs unchanged.
2. Run the existing structural validator, terminology checker and UI-writing audit automatically. These are assistant-operated checks, not tasks to give the requester.
3. Perform an actual AI review of every new/changed English/Japanese pair. For a new complete translation, review every string. Review reused wording for the current context and conventions too. Check business meaning, terminology, natural Japanese and role-appropriate style, including words not covered by an executable rule.
4. Resolve each terminology finding by meaning. Preserve distinct meanings, actor/action, negation, scope, quantities and uncertainty. Never replace words globally or force the glossary's first Japanese alternative. A zero finding count does not replace this review.
5. Correct genuine defects, then rerun the affected checks and re-review the changed text. Record deliberate retained findings and context choices with specific reasons in the normal run report/profile. An AI-reviewed context can use status `ai-reviewed`, with reviewer and actual contextual evidence; it is not user confirmation or independent Japanese-speaker approval.
6. Return the requested resource and the normal concise review summary only after the check and AI review are complete. The summary states terminology findings, AI review performed, material remaining questions and actual UI/runtime limits. Do not leave a fixable warning unexamined or ask the user to perform the language review.

If business meaning cannot be established from available evidence, explain the business question in English and identify the affected text as pending. Deliver it as a clearly marked draft, never as verified final wording. Keep independent work moving. Existing user authorization for provisional choices applies within its stated scope.

For a strict first-saved-draft evaluation, make wording decisions before saving and preserve that candidate's identity. Report any discovered post-save defect honestly; a corrected outcome must not be relabeled as the first draft.

The translating assistant performs the AI review in its current session. The local terminology checker does not call a model. No separate delivery system, model account, API key or user-run review commands are required. The process provides AI review, not independent native-speaker or rendered-layout acceptance.

The automated terminology/UI tools currently support strict JSON. For other supported resource formats, use the appropriate structural/parser checks and perform the contextual terminology review in the AI pass; state the automated coverage limitation. Preserve the requested resource format rather than converting the deliverable to satisfy a tool.
