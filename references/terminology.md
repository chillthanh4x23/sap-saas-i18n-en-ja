# Terminology and business context

Generated from terminology.json. Maintain that JSON and run render_library.py; do not edit this reading view.

These are working defaults for this skill, not a claim that every SAP product/release uses identical wording. Apply an explicit application convention first, in the appropriate business sense. Verify unfamiliar SAP-specific terms against the actual product/module's Japanese documentation.
Do not enforce glossary entries by substring replacement. For example, Invoice inside Invoice Date is not a separate requirement to insert 請求書, and Review does not always mean approval.
The structured file is the maintained source for this reference, the generated project glossary and the executable checks. A check is scoped separately from a vocabulary suggestion; a glossary row alone does not impose a universal Japanese translation.

## Context decisions

| Source concept | Recommended wording by meaning | Decision rule |
|---|---|---|
| Supplier / Vendor | 仕入先 for an SAP ERP supplier role; サプライヤー for a SaaS/product convention | Context decision. Preserve the application's agreed form, including サプライヤ if the linked SAP product uses that spelling. A convention for one application does not govern another. |
| Customer | 得意先 for SAP sales/accounting customer master; 顧客 for general SaaS customers; カスタマー if already agreed | Context decision. A customer record and a tenant organization are not interchangeable. |
| Purchase Order / PO | PO for an established compact UI abbreviation; 購買発注 when the business document needs to be explicit | Context decision. Keep PO if part of an identifier or known product label. Do not use two names randomly within one screen. |
| PO Confirmation / POC | POC for an established UI abbreviation; 購買発注確認 for explicit document/process wording | Context decision. Distinguish a supplier response from approving a PO internally. |
| Verify / Verification | 確認 for human/business checking; 検証 for technical correctness; 認証 only for an actual authentication/certification meaning | Context decision. Inspect the operation, not just the English verb. |
| Verified | 確認済み after a human/business check; 検証済み after validating correctness | Context decision. A manually reviewed extraction is not automatically an authenticated identity. |
| Validation | 検証 for correctness; 入力チェック may fit an established form-validation UI | The supplied glossary chooses 検証. Any different project convention needs the actual UI/form context and a recorded decision. |
| Confirm / Confirmation | 確認 for checking or accepting a dialog; business compounds may have their own terms | Do not turn confirmation into approval. |
| Approve / Approval / Approved | 承認 / 承認 / 承認済み | Use only where the source really grants approval. |
| Item | 明細 for document line items; 品目 for a material; 項目 for a field/list entry; アイテム only where natural and agreed | Resolve from namespace/call site. Never globally map Item to 明細. |
| Post / Posting / Posted | 転記 / 転記 / 転記済み for ERP accounting; 投稿 for a publication/social action | Do not infer accounting from the word Post alone. |
| Available | 利用可能 for a usable feature; 空き for capacity; 在庫あり for stock; 件見つかりました for search results where appropriate | Preserve the real proposition. “No results available” is usually 該当する結果がありません. |
| Successfully | Compact completed-result wording for controls/statuses; natural polite completed-result sentences for message bodies; 正常に when normal execution itself matters | Preserve completed success, distinct from action/progress. Do not mechanically insert 正常に. Follow ui-writing.md: headings compact, message bodies polite, hints clipped. |
| Submit | 送信 for sending a request; 提出 when the business process requires formal submission | Choose by the actual request flow: sending a request and formally submitting a business document can require different wording. |
| Tenant / Workspace / Organization | テナント / ワークスペース / 組織 | Keep distinct unless the product explicitly defines them as the same entity. |
| Role / Permission / Authorization / Authentication | ロール / 権限 / 認可 / 認証 | Preserve the security meaning. Do not conflate logging in with being allowed to perform an action. |
| Subscription | サブスクリプション for a SaaS plan/service; 購読 for a feed/newsletter where appropriate | Billing cancellation does not necessarily delete an account or data. |
| Deploy / Publish / Release | デプロイ / 公開 / リリース | These operations may have different effects. Use the actual product workflow. |

For unresolved context decisions, give a proposed interpretation and explain it in the user's language. If business meaning is uncertain, retain pending status and ask about the operation. A stylistic preference can be proposed and recorded without forcing a non-Japanese-speaking user to choose synonyms.

## SAP and business vocabulary

| English | Japanese draft convention | Scope / notes |
|---|---|---|
| Sales Order | 受注 | Sales business document |
| Supplier Invoice | 仕入先請求書 | If Supplier is locked as サプライヤー, consider the compound consistently in that product; do not silently change an approved document name |
| Invoice | 請求書 | Invoice document |
| Invoice Date | 請求日 | Check whether issue date is intended |
| Posting Date | 転記日 | ERP accounting |
| Document Currency | 伝票通貨 | ERP document |
| Company Code | 会社コード | SAP organizational unit |
| Cost Center | コストセンタ | Respect linked SAP product spelling |
| G/L Account | 総勘定元帳勘定 | Respect actual product label; G/L勘定 may be an agreed compact form |
| Payment Term(s) | 支払条件 | Payment conditions |
| Tax Code / Tax Amount | 税コード / 税額 | Tax fields |
| Net Amount / Gross Amount | 正味金額 / 総額 | Preserve tax-inclusive/exclusive meaning from source |
| Line Item | 明細 | Document row |
| Material / Material Master | 品目 / 品目マスタ | SAP material concept |
| Master Data | マスタデータ | Project convention; avoid drifting to マスターデータ |
| Business Partner | ビジネスパートナ | Verify exact spelling in target SAP product |
| Business Object | ビジネスオブジェクト | Business object |
| Object Type | オブジェクトタイプ | Product convention |
| Document Type | ドキュメントタイプ | Do not replace an ERP-specific 伝票タイプ without context |
| Shipment Notification | 出荷通知 | Shipping notification |
| Advance Ship Notice (ASN) | 事前出荷通知 | Keep ASN where it is an agreed abbreviation or identifier |
| Reference Data | 参照データ | Reference data |
| Workflow | ワークフロー | Workflow |
| Approver | 承認者 | Approval actor |
| Pending Approval | 承認待ち | State |
| Posting Status / Post Failed | 転記ステータス / 転記失敗 | Accounting only |
| Reprocessing | 再処理 | Process again; distinguish a mere network retry |
| Document Processing | ドキュメント処理 | Product convention |
| Document Extraction | データ抽出 | AI document extraction |
| Extraction / Extracted | 抽出 / 抽出済み | State |
| Confidence Score | 信頼度スコア | AI output confidence; do not imply guaranteed correctness |
| Duplicate Detection | 重複検知 | Detection process |
| Review | レビュー | Inspection/review without necessarily approving |
| Document Analytics / Business Analytics | ドキュメント分析 / ビジネス分析 | Analytics features |
| Email Inbox | メール受信箱 | Product inbox |
| Processing Logs | 処理ログ | Processing history |
| Batch / Job / Log | バッチ / ジョブ / ログ | IT terminology |
| Status / Error | ステータス / エラー | Generic UI |
| Draft | ドラフト | User-confirmed project convention for visible UI text, including compound phrases. Supersedes 下書き for this concept. Keep resource keys, enums and code unchanged. |


## Common UI and SaaS vocabulary

These are starting conventions, not previously user-approved decisions.

| English | Japanese | Scope |
|---|---|---|
| Save / Cancel / Close | 保存 / キャンセル / 閉じる | Actions; cancel may mean 取消 in a business cancellation workflow |
| Create / Add / Edit / Update / Delete | 作成 / 追加 / 編集 / 更新 / 削除 | Keep operations distinct; use 登録 for a registration flow where appropriate |
| Search / Filter / Sort / Refresh | 検索 / フィルタ / 並べ替え / 再読み込み | Do not confuse Refresh with updating stored data; follow an existing product convention |
| Settings / Configuration | 設定 | Distinguish configuration objects if the product does |
| Dashboard | ダッシュボード | Product overview |
| Upload / Download | アップロード / ダウンロード | Transfer direction |
| Import / Export | インポート / エクスポート | Keep distinct from upload/download |
| Export to Excel | Excel出力 | Supplied project convention |
| User / Administrator | ユーザー / 管理者 | IT audience |
| Sign in / Sign out | サインイン / サインアウト | Keep ログイン / ログアウト if that pair is established |
| Single sign-on (SSO) | シングルサインオン（SSO） | Retain SSO in compact UI where familiar |
| API key / Access token | APIキー / アクセストークン | Never translate the actual key/token value |
| Session / Timeout | セッション / タイムアウト | IT context |
| Endpoint / Webhook | エンドポイント / Webhook | Use established product spelling, e.g. ウェブフック if agreed |
| Integration / Connection | 連携 / 接続 | Application integration versus connection |
| Synchronization | 同期 | Preserve direction and scope |
| Notification / Audit log | 通知 / 監査ログ | Keep a processing log distinct from an audit log |
| Environment / Production / Sandbox | 環境 / 本番環境 / サンドボックス | Do not infer deployment targets |
| Usage / Quota | 使用量 / 上限 | Quota may require 割り当て or 割当量 by context |
| Billing / Plan | 請求 / プラン | Billing operation versus invoice document |
| Vector | ベクトル | Recommended IT wording for this package. Record any different application spelling as a scoped private convention; do not impose it on unrelated applications. |

Retain SAP, SaaS, ERP, API, URL, URI, ID, CSV, JSON, XML, HTTP, OAuth, SAML, OData and product/version names when they identify technologies or products. Do not transliterate a code, path, enum, URL, template variable or example formula.

## Convention change and reuse

The bundled Draft convention is ドラフト. An application may have a different approved convention; keep its evidence and any exact-pair exceptions in the private profile. When a convention changes, update affected maintained decisions and generated lookup views before reuse. Keep original resources and historical run evidence unchanged. Check compound phrases by meaning rather than replacing substrings in code or unrelated Japanese.


## Executable coverage

Checks are deliberately scoped. Error-level rules enforce explicit conventions; warning-level rules and unresolved context decisions require review. Unchecked glossary rows remain guidance. Longest source phrases win, so Invoice Date does not independently require Invoice. Protected syntax is excluded. See terminology-check.md for profiles, exceptions, limitations and exit codes.

| Concept | Check | Source match | Level | Scope |
|---|---|---|---|---|
| Supplier / Vendor | context-dependent | Supplier, Vendor (phrase) | warning | all applications |
| Customer | context-dependent | Customer (phrase) | warning | all applications |
| Purchase Order / PO | context-dependent | Purchase Order, PO (phrase) | warning | all applications |
| PO Confirmation / POC | context-dependent | PO Confirmation, POC (phrase) | warning | all applications |
| Verify / Verification | context-dependent | Verify, Verification (phrase) | warning | all applications |
| Verified | context-dependent | Verified (phrase) | warning | all applications |
| Validation | context-dependent | Validation (phrase) | warning | all applications |
| Item | context-dependent | Item, Items (phrase) | warning | all applications |
| Post / Posting / Posted | context-dependent | Post, Posting, Posted (phrase) | warning | all applications |
| Available | context-dependent | Available (phrase) | warning | all applications |
| Submit | context-dependent | Submit (phrase) | warning | all applications |
| Subscription | context-dependent | Subscription (phrase) | warning | all applications |
| Sales Order | required | Sales Order (exact) | warning | all applications |
| Supplier Invoice | context-dependent | Supplier Invoice (phrase) | warning | all applications |
| Invoice | required | Invoice (exact) | warning | all applications |
| Invoice Date | required | Invoice Date (exact) | warning | all applications |
| Posting Date | required | Posting Date (exact) | warning | all applications |
| Document Currency | required | Document Currency (exact) | warning | all applications |
| Company Code | required | Company Code (exact) | warning | all applications |
| Cost Center | required | Cost Center (exact) | warning | all applications |
| Payment Term(s) | required | Payment Term(s) (exact) | warning | all applications |
| Line Item | required | Line Item (exact) | warning | all applications |
| Master Data | deprecated | Master Data (phrase) | warning | all applications |
| Business Partner | required | Business Partner (exact) | warning | all applications |
| Business Object | required | Business Object (exact) | warning | all applications |
| Object Type | required | Object Type (exact) | warning | all applications |
| Document Type | context-dependent | Document Type (phrase) | warning | all applications |
| Shipment Notification | required | Shipment Notification (exact) | warning | all applications |
| Advance Ship Notice (ASN) | required | Advance Ship Notice (ASN) (exact) | warning | all applications |
| Reference Data | required | Reference Data (exact) | warning | all applications |
| Workflow | required | Workflow (exact) | warning | all applications |
| Approver | required | Approver (exact) | warning | all applications |
| Pending Approval | required | Pending Approval (exact) | warning | all applications |
| Reprocessing | required | Reprocessing (exact) | warning | all applications |
| Document Processing | required | Document Processing (exact) | warning | all applications |
| Document Extraction | required | Document Extraction (exact) | warning | all applications |
| Confidence Score | required | Confidence Score (exact) | warning | all applications |
| Duplicate Detection | required | Duplicate Detection (exact) | warning | all applications |
| Review | required | Review (exact) | warning | all applications |
| Email Inbox | required | Email Inbox (exact) | warning | all applications |
| Processing Logs | required | Processing Logs (exact) | warning | all applications |
| Draft | required | Draft, Drafts (phrase) | error | all applications |
| Dashboard | required | Dashboard (exact) | warning | all applications |
| Synchronization | required | Synchronization (exact) | warning | all applications |
