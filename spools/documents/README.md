# Bounded document chain

English · [简体中文](README.zh-CN.md)

Version 1 supports text PDF EUR line-item quotes with a title, Currency EUR,
Item Quantity Unit price, then one item/quantity/price per line. Missing currency and quantities may be filled only from an authorized user
clarification input. Other currencies, OCR and general workbook editing are outside
this contract. Quote totals are bounded to EUR 10,000,000,000.00 for exact cached
workbook arithmetic. Domain source
has no provider or runtime-management dependency.

The portable body extracts PDF text, checks a proposed Markdown table against
source facts, checks structured rows against accepted Markdown, generates XLSX,
and independently verifies workbook cells, formulas, cached totals and provenance.
The locked pypdf/XlsxWriter wheels are operator-provisioned offline dependencies
for guest extraction/authoring. `delivery.json` declares the fixed guest actions, prompts and clarification fields.
`pack-delivery.py --loom PATH --output NEW_DIRECTORY` builds and verifies two
independent native acceptance releases through Loom: Markdown checks the original
PDF plus authorized answers (AN_SPOOL_AUX_0/1), while workbook checks accepted
Markdown (AN_SPOOL_AUX_0). Both retain the domain body and emit verification.json;
Markdown needs the pinned pypdf site and workbook uses the standard library.
The legacy root native entry remains the workbook verifier. Dependency archives,
images, profiles, credentials, raw sessions and generated documents stay private.

Run the domain tests with the selected dependency site on PYTHONPATH, then use
Loom check/pack/verify and export-native-spool-v3. Static packaging grants no
execution authority. A real-model/VM chain is separately qualified; package checks
alone make no claim about host termination, model behavior or product custody.
The source and provider usage remain subject to their individual licenses;
requirements.lock.json records acquisition identities, not a security audit.
