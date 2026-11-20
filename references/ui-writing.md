# Compact Japanese UI wording for IT / SAP users

The package default is role-specific Japanese: compact controls and natural, concise message bodies. Use familiar SAP/IT terminology, short noun or action endings (体言止め), and the shortest wording that preserves the source meaning. Apply this pass to reused library text as well as new translations. A previous semantic review does not certify compactness or screen fit.

## Match the UI function

| Function | Required direction | Examples |
|---|---|---|
| Button/action | Noun or short object + action noun; omit polite sentence/request endings | 保存, 承認, 新リクエストを作成 |
| Field/table header/tab/menu/title | Compact, unambiguous noun phrase. This includes headings of status, result, error and empty-state areas | 作成日時, 作成者, リクエスト一覧, 作成完了, 重複なし |
| Status/progress | Short state/result phrase; keep state distinct from action | 承認待ち, 確認済み, 処理中, 保存完了 |
| Helper text/tooltip/placeholder/empty-state text | Clipped instruction or phrase is correct; it must stay clear: object + action, no dropped condition/order/scope, no dangling particle, one pattern per screen | フィールドを選択, フィールドを追加してデータ構造を定義, 検証ルール未設定。上のボタンでルール追加 |
| Success notification body | Brief natural completed-result sentence; its heading/badge is compact | 保存しました。 |
| Error/warning body | Natural short sentences for the failure and source-provided next action; preserve negation | 保存できません。入力内容を確認してください。 |
| Confirmation | Keep the question and required object/scope/consequences; a short question is allowed | 選択項目を削除？ |
| Activity/history | Short event label; do not turn an event into a current-state badge | 承認, 差戻し, 更新 |
| Accessibility | Concise accessible action/name while keeping necessary context | フィルタを解除 |

The compact style is illustrated by 新しいリクエストを作成します → 新リクエストを作成. This is a UI style example, not a global string-replacement rule. Use established Japanese compounds and preserve the product's actual entity name.

For notification, error, success and explanatory bodies, prefer concise natural sentences with です／ます and 〜してください where appropriate. Keep headings, badges and button text distinct from body text. Do not force nominal endings onto message bodies. Hints, placeholders and empty-state text stay clipped; headings stay compact in every context. These role distinctions apply throughout the UI.

## Compactness pass

1. Identify the element role from the call site, supplied role mapping or resource context. A key-name guess is evidence for triage, not confirmation of the rendered element.
2. For buttons, labels, headings and statuses, remove unnecessary sentence framing such as ～します, ～です or ～してください by rewriting the full phrase in context.
3. For guidance and messages, remove redundant subjects, literal possessives, explanatory padding and repeated product names. Keep useful instructions and the source's sequence of actions.
4. Prefer established short terms and parallel wording within a control/state family. Keep placeholders, technical identifiers and business terminology exact.
5. Check the resulting Japanese against English again. Compactness must preserve actor, action, object, polarity, condition, time, quantity and certainty.

Never implement this pass by stripping Japanese suffixes mechanically. Removing a negative ending can reverse a permission or failure statement. Distinguish an unavailable action, a failed attempt and a completed action. Do not delete only, except, after success, all, selected, cannot be undone, or a retry instruction merely to shorten the UI.

## Length and layout budget

Keep Japanese close to the English element's display budget. Shorten avoidable expansion before delivery, including when a reused reference is grammatically correct.

- Use an actual component width, line limit and font when available. Check wrapping, clipping, ellipsis and runtime variable values on the real UI.
- Raw character counts are not equivalent to rendered width across English and Japanese. Do not infer that a shorter character count guarantees a smaller label.
- Without the UI, the bundled JSON audit estimates literal display cells: wide/full-width characters count as two, most Latin characters as one, combining marks as zero. This is a triage estimate, not pixel measurement.
- The role-aware audit checks width only for buttons, labels, headings and statuses. Its default budget is the larger of 12 cells or 1.5 times the estimated English width; overflow of up to 2 cells is info only, and exact standardTerms are exempt. Message bodies may wrap and are not width-checked. These are adjustable project heuristics, not SAP/Japanese standards or proven component limits. (The legacy compact style used 1.25 times with an eight-cell minimum.)
- Placeholders and markup are excluded from the literal-width estimate. Their runtime size and rendering are not checked. Invisible accessibility text is not constrained by a visible control's width.
- A width finding requires a shorter draft or a specific retained-wording reason. Never truncate text or remove a condition automatically to satisfy the ratio.

Use scripts/audit-ui-writing.py for read-only JSON triage. The structural validator remains a separate check. If actual UI rendering is unavailable, report layout as not tested even when the heuristic finds no issues.

## Preserve the business proposition

- A pending process is not automatically pending approval.
- A manually checked document is not automatically authenticated or approved.
- A posting state and a posting timestamp need different meanings even if both use the English Posted.
- Remove from a group or pending message is not automatically permanent file deletion.
- A request timeout concerns processing duration, not input-text length.
- A negative permission, an irreversible consequence and the scope of selected records remain explicit.
- Preserve amounts, currencies, dates, units, thresholds, comparisons and uncertainty.

## Reuse and review boundaries

Apply current UI style requirements after scoped terminology/meaning lookup. An old app-specific sentence does not bypass the latest compact-UI request. Preserve its business decision and terminology, then review its form for the target element. When resource editing is outside scope, report style findings without rewriting the Japanese.

Existing compactness, source/key parity and native-language quality are separate questions. Review all changed/reused text for the current element role; inspect concatenated fragments as a full message when possible. Record unresolved role, runtime or layout questions. Do not claim first-pass UI acceptance from a byte-identical library reconstruction or a zero structural-error count.

## Role-aware audit

audit-ui-writing.py defaults to `style: role-aware`. `style: compact` keeps the legacy heuristic for reproducing older runs.

Role order (first match wins): profile `rolesByKey` (high confidence) → profile `rolesByPattern`, longest glob first (high) → built-in key rules (medium) → same English elsewhere, from a duplicate-text report via `--peers` (medium/low) → English shape (low). Groups marked as separate meanings or UI roles by semantic review never share roles. Confidence drops to low when the key name and the English disagree. Low-confidence findings are listed first: confirm those roles in the app profile.

| Finding | Roles | Flags when | Level |
|---|---|---|---|
| control-sentence-ending | action, label, heading, status (headings in status/result/error/empty areas included) | Ends in ます/です/ください/ました | needs review |
| action-verb-ending | action | Ends in する/します | needs review |
| control-full-stop | controls | Ends with 。 | info |
| message-note-style | message, confirmation | The English is a sentence but the Japanese has no polite ending (a short confirmation question ending in ？ is allowed) | needs review |
| request-form-missing | message, confirmation | The English asks the user to act; the Japanese has no ください-type request | needs review |
| formal-phrasing | sentence roles | お願いいたします, くださいませ, することができます etc. (してください is never flagged) | info |
| sentence-full-stop-missing | message, confirmation | The English ends with punctuation; the Japanese has no 。 | info |
| estimated-width-growth | controls | Over the width budget; ≤2 cells over is info | needs review / info |

Values without Japanese text (English fallbacks, codes) are skipped; the structural validator reports them. Trailing placeholders are ignored when checking an ending.

Profile `uiWriting` fields: `style`, `rolesByKey`, `rolesByPattern`, `provisionalRolesByKey`, `widthBudget` (`minimumCells`, `growthRatio`, `toleranceCells`, `roles`), `standardTerms`, `exceptionsByKey` (exact source/target, codes and reason). Store application profiles outside this shared package.

`provisionalRolesByKey` records contain `role`, exact English `source`, `reason` and `status: provisional`. Confirmed exact-key roles take priority; provisional keys then precede patterns and inference. Provisional choices always retain low confidence and a visible pending-confirmation note. A changed or removed source key invalidates the choice. Do not promote temporary AI choices into confirmed `rolesByKey` merely to clear findings.

Hints, placeholders and empty-state text are not checked for endings or request forms: clipped instructions are correct there. Their clarity (object + action, kept conditions, no dangling particle) is checked in the meaning review, not by this script.

Known inference limits: sentence-like text without punctuation under status keys can still get a control role; all roles remain inferred from resources, not call sites.

References: [Microsoft Japanese localization guide, sections 4.2 and 5.3.2](https://download.microsoft.com/download/a/8/2/a822a118-18d4-4429-b857-1b65ab388315/jpn-jpn-StyleGuide.pdf) and [SAP message-writing guidance, beta](https://www.sap.com/design-system/fiori-design-web/v1-148/foundations/writing-and-wording/ux-writing/ux-writing-guidelines/ui-text). Microsoft guidance is Japanese-specific; SAP English word order and capitalization are not Japanese grammar rules.
