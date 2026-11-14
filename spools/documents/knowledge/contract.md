# Document chain v1

English · [简体中文](contract.zh-CN.md)

Use one primary session. Read the permitted source text and preserve every row.
Produce a Markdown pipe table with exactly Item, Quantity, Unit price (EUR).
Quantities are positive integers; prices are nonnegative decimal EUR with at most
two decimal places. Currency must be explicitly EUR. Ask when facts are missing. A source may report requires_clarification keys; user answers must arrive through an authorized clarification input, never invented proposal fields.
Do not add totals as data rows. Outside the table, use only an optional source title heading and Currency: EUR. Markdown is a proposal until the host accepts it.

On the next turn, read the accepted Markdown through the host artifact reference.
Propose JSON containing source_sha256 and rows. Each row contains only item,
quantity and unit_price. Copy source_sha256 from the accepted Markdown bytes;
never infer an artifact identity from a path. The program computes amounts and
totals. The host validates the workbook before delivery. No model child agents.
