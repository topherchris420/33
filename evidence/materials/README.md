# Procurement record

`invoices.json` contains actual purchase records only. No invoices have been supplied. The ten BOM lines and $81 subtotal remain estimates. The ledger is separate from the Observatory claim registry; the release audit reads it without changing claim status or D-021.

For each actual paid invoice, record `invoice_id`, `vendor`, `purchased_on` (YYYY-MM-DD), `transaction_status` (`paid`), `document` (`path` under `evidence/materials/receipts/` and `sha256`), and `lines`. Each line needs `item` matching the BOM exactly, `quantity`, and `line_total_usd` as a decimal string. The release audit reconciles quantities and totals against the BOM's purchased unit price. Record tax, shipping, spares and reused inventory separately; the current acquisition subtotal covers listed BOM parts only. Do not insert mock transactions here.

A document digest detects changed bytes. It does not authenticate the vendor, establish payment, or resolve the five-versus-six servo mismatch or SG90/MG996R specification mismatch in D-021. Those require an as-built inventory and human review.
