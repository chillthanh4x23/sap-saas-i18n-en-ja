# Sources, provenance and scope

The bundled glossary and writing guidance are working defaults for SAP and B2B SaaS localization. They are not a universally verified Japanese dictionary. Application-specific decisions require evidence for the actual business meaning and product context; they belong in the consuming project's private profile, not in this shared package.

Examples and test fixtures use synthetic data. Customer resources, internal application names, private review records and local filesystem layouts are not part of the distribution. Ask the requester about unresolved business meaning, rather than asking someone who cannot read Japanese to choose synonyms.

## Japanese naturalness reference

Some writing principles are adapted from the publicly available coji/natural-japanese project: preserve facts and certainty, avoid literal English constructions, use established technical names, and judge wording in context.

Do not import its full document-writing workflow, prose-rhythm rules, automatic research, critical-thinking workflow or large experimental model downloads into i18n translation. UI structure, consistent labels and runtime integrity take precedence.

The upstream work is MIT-licensed. Its notice is retained in [THIRD_PARTY_NOTICES.txt](../THIRD_PARTY_NOTICES.txt). This package does not copy its Python scripts or require that repository at runtime.

## Primary documentation consulted

- [i18next interpolation](https://www.i18next.com/translation-function/interpolation): variables, escaping flags and configurable syntax.
- [i18next plurals](https://www.i18next.com/translation-function/plurals): locale-dependent plural resolution. Inspect the actual installed version before changing schemas.
- [i18next localization best practices](https://www.i18next.com/principles/best-practices): context and problems caused by concatenated fragments.
- [ICU MessageFormat](https://unicode-org.github.io/icu/userguide/format_parse/messages/): typed arguments, plural/select messages and escaping. MessageFormat variants need their actual parser.
- [SAPUI5 translatable texts, version 1.38.65](https://ui5.sap.com/1.38.65/docs/guide/df86bfbeab0645e5b764ffa488ed57dc.html): resource properties and indexed arguments. This is a versioned reference, not a claim about the latest encoding behavior.
- [SAP Master Data Governance customer/supplier integration](https://help.sap.com/docs/SAP_MASTER_DATA_GOVERNANCE/fe69af2ae6534e0aa7559a69dd84b7ea/d8ff96525452225ce10000000a44538d.html?locale=ja-JP): Japanese 得意先/仕入先 terminology in that context.
- [SAP S/4HANA Cloud document-splitting item categories](https://help.sap.com/docs/SAP_S4HANA_CLOUD/0fa84c9d9c634132b7c4abb9ffdd8f06/18876fc36c974906ab1c1b60722d5bb0.html?locale=ja-JP): illustrates product-specific サプライヤ wording as well as 得意先.
- [Microsoft Entra external-tenant features, Japanese](https://learn.microsoft.com/ja-jp/entra/external-id/customers/concept-supported-features-customers): examples of familiar IT vocabulary including テナント, ロール and シングル サインオン.

Public sources support framework behavior and examples of terminology. The choices in this package remain draft product conventions; do not present them as one universal official SAP dictionary. For an uncertain term, consult the Japanese documentation of the target product/module first and retain the supporting link in the decision report.
