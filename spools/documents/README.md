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
for guest extraction/authoring. The native spool entry uses only Python's standard
library to verify an XLSX candidate against operator-selected accepted Markdown
(AN_SPOOL_AUX_0) and emits result.xlsx plus verification.json. Dependency archives,
images, profiles, credentials, raw sessions and generated documents stay private.

Run the domain tests with the selected dependency site on PYTHONPATH, then use
Loom check/pack/verify and export-native-spool-v3. Static packaging grants no
execution authority. A real-model/VM chain is separately qualified; package checks
alone make no claim about host termination, model behavior or product custody.
The source and provider usage remain subject to their individual licenses;
requirements.lock.json records acquisition identities, not a security audit.
