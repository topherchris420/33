# Utility Bench Manual reference

[Open the searchable manual](../lab/bench-manual.html#reference).

The existing film now has a nine-chapter reading companion: scope and revision,
system description, offline review, abnormal records, instrumentation,
limitations, configuration, sessions, and foldout references. It indexes Project
33 documents and provides a glossary of evidence and audit terminology. Every
chapter has a review checklist. System descriptions explain the rocket processor,
launcher, dashboard and Evidence Observatory. Seven symptom-based troubleshooting
entries distinguish interpretation from record review and link to the source.

Search covers chapter prose, source paths and glossary definitions. Chapter links
can be bookmarked. Reading marks stay in this browser, reset when the indexed
edition changes, and never update the evidence record. If browser storage is
unavailable, marks work for the current page only. Print reference clears the
search and opens the troubleshooting details so the complete reading guide is printed.

## Sources and revision control

`tools/build_bench_manual.py` owns the original summaries, chapter structure and
glossary. `lab/data/bench_manual.json` is generated: every linked document has its
SHA-256 recorded. The edition digest covers the summaries and source index.

```text
python tools/build_bench_manual.py
python tools/build_bench_manual.py --check
```

Regenerate after editing any referenced document. The automated freshness test
detects drift. A source digest identifies bytes; it is not scientific validation.
The online document links resolve to the currently published site; the displayed
digest describes the indexed edition, not a live verification of the destination.

## Historical study and coverage

The supplied scan was identified visually as the OCIP supplement, TO 1F-117A-1A,
Issue B, rather than the complete base flight manual. It has 87 PDF image pages;
the publication's own effective-page count and printed labels are different.
Its organization includes revision records, descriptions, normal and abnormal
procedures, equipment, glossary, index and foldouts. Some subjects refer back to
the base manual rather than supplying their content in this supplement.

REA was attempted on the supplied PDF and returned `target_unavailable`,
`unsupported_target`, `file_format_rejected`. It supplied no document-content
evidence. Separate PDF extraction established that the scan has no extractable
text; local OCR processed 87 images. OCR is noisy and diagrams were not reliably
transcribed. Visual inspection established the cover, scope and organization;
this is not a verified transcription or exhaustive technical interpretation.

The implemented adaptation uses generic document organization and original
Project 33 summaries. Aircraft procedures, navigation logic, operating limits,
weapons content and illustrations are not technical inputs to Project 33.
See the existing [source audit](LIVING_LAB.md#source-rights-audit). The scan and
OCR working files are not published.

## Validation

`tests/test_bench_manual.py` checks reproducibility, source identity and chapter
coverage. The existing laboratory isolation tests cover this page's scripts.
`tests/lab_browser/bench-manual.mjs` checks search, glossary-only results,
deep links, reading persistence/reset, mobile layout and the film source.

The manual has no hardware interface and records no observations or approvals.
It does not establish physical performance or replace the linked source records.
