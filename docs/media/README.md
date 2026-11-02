# Project 33 public flier

[Project 33 Issue B flier](project33-issue-b-flier.pdf) is the original, two-page
PDF supplied by the project owner as `Project 33 flier design.pdf`.
Its bytes have been preserved unchanged.

| Property | Value |
|---|---|
| Document identifier | V3D-TO-33-1B |
| Pages | 2, US Letter |
| Size | 648,149 bytes |
| SHA-256 | `39339f3073dce16955d8493799d4f16eea97614669c0ac68967017eb849d5798` |

The flier is a concept and proposal document. Its Issue B integration list does
not record completed implementation or accepted physical measurements. Dimensions,
stability, and cost shown on the artwork remain design or estimated values;
the [claim passports](../claims/README.md), [discrepancy register](../DISCREPANCIES.md),
and [BOM](../BOM.md) provide the current evidence and limitations.

## README previews

The [first-page preview](../../assets/marketing/project33-flier-page-1.png) and
[second-page preview](../../assets/marketing/project33-flier-page-2.png) are direct
Poppler renders, with no changes to the text or illustrations. To render them again
from the repository root with Poppler installed:

```bash
pdftoppm -scale-to 1400 -png docs/media/project33-issue-b-flier.pdf assets/marketing/project33-flier-render
```

This produces `project33-flier-render-1.png` and `project33-flier-render-2.png`.
After inspection, replace the corresponding `project33-flier-page-1.png` and
`project33-flier-page-2.png` previews. Rendering can vary with the Poppler version;
the PDF digest above identifies the source document.

[Project README](../../README.md)
