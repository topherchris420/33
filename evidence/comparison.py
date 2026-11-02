"""Readable review comparisons; all values come from verified packet snapshots."""

from html import escape
import json


def _cell(value):
    text = escape(str(value), quote=False)
    for char in "\\`*_[]|~":
        text = text.replace(char, "\\" + char)
    return text.replace("\r", " ").replace("\n", " ")


def comparison_markdown(change):
    lines = ["# Project 33 · Review comparison", "", change["meaning"], "",
             "Both packets passed file-integrity verification. This does not authenticate their authors "
             "or establish scientific validity.", "", "## Review scope", "",
             "| Item | Change |", "|---|---|"]
    for title, key in (("Affected claims", "affected_claims"),
                       ("Artifact bytes", "changed_artifacts"),
                       ("Artifact descriptions or classifications", "changed_artifact_records"),
                       ("Record files", "changed_record_files"),
                       ("Discrepancies", "discrepancy_changes")):
        lines.append(f"| {title} | {_cell(', '.join(change[key])) if change[key] else 'None detected'} |")
    for title, key in (("Review context", "review_context_changed"),
                       ("Reviewer implementation", "reviewer_changed"),
                       ("Provenance", "provenance_changed")):
        lines.append(f"| {title} | {'Changed' if change[key] else 'Unchanged'} |")
    lines += ["", "Changed record files can contain changes beyond the claim mapping above; "
              "inspect those records even when no affected claim is listed.", "", "## Claim status", ""]
    if change["claim_status_changes"]:
        lines += ["| Claim | Before | After |", "|---|---|---|"]
        for item in change["claim_status_changes"]:
            lines.append("| " + " | ".join(_cell(item[key]) for key in ("claim", "before", "after")) + " |")
    else:
        lines.append("No claim status changes detected.")
    lines += ["", "## Requirement changes", "",
              "A requirement can change while retaining the same pass/fail result.", ""]
    if not change["requirement_details"]:
        lines.append("No evaluated requirement changes detected.")
    for item in change["requirement_details"]:
        lines += ["### " + _cell(item["requirement"]), "", "| Field | Before | After |", "|---|---|---|"]
        for field in item["changed_fields"]:
            cells = [_cell(field)]
            for side in ("before", "after"):
                record = item[side] or {}
                cells.append(_cell(json.dumps(record[field], ensure_ascii=False, sort_keys=True))
                             if field in record else "Not present")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
