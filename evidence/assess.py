"""Assemble one assessment from the record, the artifacts, and optional run records.

Hard errors (a claim promoted beyond its evidence, relabeled synthetic data)
stop the build: no report is safer than a misleading one. Soft violations
(stale reviews, drifted predictions, failed consistency checks) are shown in the
report and make `python -m evidence check` fail.
"""

from collections import Counter

from .common import EvidenceError
from . import evaluate as E
from . import vocabulary as V


def _consistency(check, records, data):
    left, _ = E.extract(check["left"], records, data)
    right, _ = E.extract(check["right"], records, data)
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != 1 or len(right) != 1:
        return {"id": check["id"], "description": check["description"], "claims": check["claims"],
                "result": "failed", "left": None, "right": None,
                "detail": "a side could not be extracted as a single value"}
    ok = abs(left[0] - right[0]) <= check["tolerance"]
    return {"id": check["id"], "description": check["description"], "claims": check["claims"],
            "result": "passed" if ok else "failed", "left": left[0], "right": right[0],
            "tolerance": check["tolerance"]}


def _reproduction_scope(reproduction, artifacts):
    if reproduction is None:
        return "not_run", "MODEL REPRODUCTION — NOT RUN BY THIS BUILD; run python -m evidence reproduce (needs model dependencies)"
    current = {a["id"]: a["sha256"] for a in artifacts}
    stale = [r["artifact"] for r in reproduction["results"] if current.get(r["artifact"]) != r["committed_sha256"]]
    failed = [r["artifact"] for r in reproduction["results"] if r["result"] != "reproduced"]
    if stale:
        return "stale", f"MODEL REPRODUCTION STALE — record describes different artifact bytes: {', '.join(stale)}"
    if failed:
        return "failed", f"MODEL REPRODUCTION FAILED — not reproduced: {', '.join(failed)}"
    return "passed", f"MODEL REPRODUCED — {len(reproduction['results'])} committed model outputs regenerated and matched"


def assess(records, data, *, provenance, execution=None, reproduction=None):
    hard, violations = [], []

    def violation(code, message, claims=()):
        violations.append({"code": code, "message": message, "claims": sorted(claims)})

    artifacts = [E.inspect_artifact(item, data[key]) for key, item in sorted(records.artifacts.items())]
    lookup = {a["id"]: a for a in artifacts}
    accepted = E._accepted_measurements(records)

    requirements = {}
    for key, req in sorted(records.requirements.items()):
        result = E.evaluate_requirement(req, records, data, execution, accepted)
        result["label"] = V.REQUIREMENT_RESULTS[result["result"]]
        result["claims"] = req["claims"]
        result["source"] = req["source"]
        result["quantity"] = req.get("quantity")
        result["assumptions"] = req["assumptions"]
        result["implementation"] = req["implementation"]
        result["tests"] = req["tests"]
        result["check_label"] = V.CHECK_TYPES[req["check"]]
        if result.pop("missing_value", False):
            violation("missing_value", f"{key}: {result['reason']}", req["claims"])
        requirements[key] = result

    consistency = [_consistency(check, records, data) for check in records.catalog.get("consistency", [])]
    for item in consistency:
        if item["result"] != "passed":
            violation("consistency_failed", f"{item['id']}: {item['description']}", item["claims"])

    predictions = {key: E.compare_prediction(pred, records, data, accepted)
                   for key, pred in sorted(records.predictions.items())}
    for item in predictions.values():
        item["result_label"] = V.COMPARISON_RESULTS[item["result"]]
        if item["drift"]:
            violation("prediction_drift", f"{item['id']}: {item['drift']}. Register a new prediction and "
                      "supersede this one; never edit a registered value.", item["claims"])

    discrepancies = sorted(records.discrepancies.values(), key=lambda d: d["id"])
    claims = []
    for key, claim in sorted(records.claims.items()):
        results = [requirements[ref] for ref in claim["requirements"]]
        linked = [d for d in discrepancies if key in d["claims"]]
        fresh = E.freshness(claim, records, data)
        level = E.support_level(claim, records, results, accepted)
        allowed = E.allowed_gate(claim, records, accepted, fresh)
        if V.GATE_INDEX[claim["gate"]] > allowed:
            hard.append(f"{key} claims gate {claim['gate']} but its records only support "
                        f"{V.GATES[allowed][0] if allowed >= 0 else 'no gate'}")
        errors, soft = E.status_findings(claim, results, linked)
        hard.extend(errors)
        for message in soft:
            violation("status_stale", message, [key])
        if fresh["state"] == "never_reviewed":
            violation("review_missing", f"{key}: no review record exists. Record one with "
                      "python -m evidence snapshot.", [key])
        elif fresh["state"] != "current":
            detail = ", ".join(V.FRESHNESS[state] for state in fresh["states"])
            changed = f" ({', '.join(fresh['changed'])})" if fresh["changed"] else ""
            violation("review_not_current", f"{key}: {detail}{changed}. The previous review is no longer "
                      "sufficient; this does not make the claim false.", [key])
        classes = sorted({lookup[ref]["class"] for ref in claim["evidence"]},
                         key=lambda c: (V.EVIDENCE_CLASSES[c]["rank"], c))
        dependencies = E.claim_dependencies(claim, records)
        claims.append({
            **claim,
            "status_label": V.CLAIM_STATUSES[claim["status"]][0],
            "status_meaning": V.CLAIM_STATUSES[claim["status"]][1],
            "gate_label": V.GATE_LABELS[claim["gate"]],
            "support": level, "support_label": V.SUPPORT_LABELS[level],
            "evidence_classes": classes,
            "has_accepted_physical_evidence": level in ("bench_observed", "bench_measured", "independently_reviewed"),
            "has_synthetic_only_data": "synthetic" in classes,
            "requirement_results": [{k: r[k] for k in ("id", "result", "label", "evidence_class")} for r in results],
            "discrepancies_open": [d["id"] for d in linked if d["status"] == "open"],
            "discrepancies_resolved": [d["id"] for d in linked if d["status"] != "open"],
            "known_contradictions": [r["id"] for r in results if r["result"] in ("not_satisfied", "conflicting")]
            + [d["id"] for d in linked if d["status"] == "open" and d["effect"] == "contradicts_claim"],
            "preregistrations": sorted(p["id"] for p in records.preregistrations.values() if key in p["claims"]),
            "freshness": fresh,
            "freshness_label": V.FRESHNESS[fresh["state"]],
            "affected_by_changes": sorted(records.artifacts[ref]["path"] for ref in dependencies),
            "not_established": _not_established(level),
        })

    if hard:
        raise EvidenceError("Record promotes beyond its evidence: " + "; ".join(hard))

    physical = sum(V.EVIDENCE_CLASSES[a["class"]]["physical"] for a in artifacts)
    accepted_physical = sum(1 for m in records.measurements.values())
    result_counts = Counter(r["result"] for r in requirements.values())
    status_counts = Counter(c["status"] for c in claims)
    machine = [r for r in requirements.values() if r["check"] == "machine"]
    reproduction_state, reproduction_text = _reproduction_scope(reproduction, artifacts)
    if execution is None:
        tests_state, tests_text = "not_run", "SOFTWARE TESTS — NOT RUN BY THIS BUILD; attach a JUnit record with --execution-record"
    elif execution["failed"]:
        tests_state, tests_text = "failed", f"SOFTWARE TESTS FAILED — {execution['failed']} of {execution['tests']} tests failed"
    else:
        tests_state, tests_text = "passed", (f"SOFTWARE TESTS PASSED — {execution['passed']} passed, "
                                             f"{execution['skipped']} skipped (skipped is not passed)")
    scopes = [
        {"id": "bundle_integrity", "state": "passed",
         "text": "BUNDLE INTEGRITY — sealed at build; re-check anywhere with python -m evidence verify"},
        {"id": "record_schema", "state": "passed", "text": "RECORD SCHEMA VALID — every record file parsed and cross-referenced"},
        {"id": "record_consistency", "state": "failed" if violations else "passed",
         "text": (f"RECORD CONSISTENCY FAILED — {len(violations)} finding(s) below" if violations
                  else "RECORD CONSISTENCY PASSED — no drift, stale review, or failed consistency check")},
        {"id": "requirements_evaluated", "state": "partial",
         "text": (f"REQUIREMENTS — {len(machine)} of {len(requirements)} machine-evaluated from committed artifacts; "
                  f"{result_counts['requires_human_review']} need human review; "
                  f"{result_counts['not_measured']} need physical measurement")},
        {"id": "software_tests", "state": tests_state, "text": tests_text},
        {"id": "model_reproduction", "state": reproduction_state, "text": reproduction_text},
        {"id": "firmware_build", "state": "not_run",
         "text": "FIRMWARE BUILD — NOT RUN BY THIS BUILD (CI job 'PlatformIO firmware build'); compiling is not hardware behavior"},
        {"id": "physical_performance", "state": "not_established",
         "text": (f"PHYSICAL PERFORMANCE — NOT ESTABLISHED; {accepted_physical} accepted inert measurements"
                  if not accepted_physical else
                  f"PHYSICAL PERFORMANCE — {accepted_physical} accepted inert measurements; see comparisons")},
        {"id": "flight_readiness", "state": "not_assessed",
         "text": "FLIGHT READINESS — NOT ASSESSED; outside this repository's validation boundary"},
    ]

    return {
        "schema_version": 2, "kind": "project_review", "project": records.catalog["project"],
        "scope": records.catalog["scope"], "provenance": provenance,
        "artifacts": artifacts, "claims": claims,
        "requirements": list(requirements.values()), "predictions": list(predictions.values()),
        "consistency": consistency, "discrepancies": discrepancies,
        "preregistrations": sorted(records.preregistrations.values(), key=lambda p: p["id"]),
        "sessions": sorted(records.sessions.values(), key=lambda s: s["id"]),
        "measurements": sorted(records.measurements.values(), key=lambda m: m["id"]),
        "archive": sorted(records.archived.values(), key=lambda a: a["path"]),
        "recipes": records.catalog.get("recipes", []),
        "records_kept": sorted(records.declared),
        "execution_record": None if execution is None else {k: v for k, v in execution.items() if k != "outcomes"},
        "reproduction_record": reproduction,
        "violations": violations, "scopes": scopes,
        "counts": {
            "claims": len(claims), "artifacts": len(artifacts),
            "current_artifacts": sum(a["status"] == "current" for a in artifacts),
            "declared_physical_artifacts": physical,
            "accepted_physical_measurements": accepted_physical,
            "claim_status": dict(sorted(status_counts.items())),
            "unresolved_claims": sum(c["status"] in ("open", "contradicted") for c in claims),
            "requirement_results": dict(sorted(result_counts.items())),
            "discrepancies_open": sum(d["status"] == "open" for d in discrepancies),
            "discrepancies_total": len(discrepancies),
            "predictions_not_measured": sum(p["result"] == "not_measured" for p in predictions.values()),
            "predictions_total": len(predictions),
            "archived_items": len(records.archived),
        },
        "questions": questions(claims, requirements, predictions, discrepancies, records),
        "vocabulary": {
            "evidence_classes": V.EVIDENCE_CLASSES, "claim_statuses": {k: list(v) for k, v in V.CLAIM_STATUSES.items()},
            "gates": [list(g) for g in V.GATES], "freshness": V.FRESHNESS, "requirement_results": V.REQUIREMENT_RESULTS,
            "comparison_results": V.COMPARISON_RESULTS, "support_levels": [list(s) for s in V.SUPPORT_LEVELS],
        },
        "principles": V.PRINCIPLES, "ai_boundary": V.AI_BOUNDARY,
        "limitations": [
            "Artifact presence and hash integrity are not scientific validation.",
            "Evidence classes, claim statuses, assumptions, and discrepancies are authored declarations checked for internal consistency.",
            "This build evaluates recorded values; it does not run models, tests, firmware, or hardware unless run records are attached.",
            "A digest detects change against a trusted reference; it is not a signature.",
            "No flight readiness, certification, or agency endorsement is asserted.",
        ],
    }


def _not_established(level):
    items = ["Physical performance of any hardware.", "Flight readiness or safety for live propulsion."]
    if level in ("none", "implementation", "model", "software"):
        items.insert(0, "Any inert physical measurement: none has been accepted for this claim.")
    return items


def questions(claims, requirements, predictions, discrepancies, records):
    """Grounded answers derived only from the record. No generated prose."""
    by_level = lambda levels: [c["id"] for c in claims if c["support"] in levels]  # noqa: E731
    depends = {}
    for claim in claims:
        for path in claim["affected_by_changes"]:
            depends.setdefault(path, []).append(claim["id"])
    return [
        {"id": "unresolved", "question": "Which claims are unresolved, and why?",
         "answer": [{"claim": c["id"], "status": c["status_label"], "because": c["concerns"] + c["known_contradictions"]}
                    for c in claims if c["status"] in ("open", "contradicted")]},
        {"id": "model_only", "question": "Which claims rest only on models or implementation, with no accepted physical evidence?",
         "answer": by_level(("none", "implementation", "model", "software"))},
        {"id": "conflicts", "question": "Which requirements currently conflict with their results?",
         "answer": [{"requirement": r["id"], "result": r["label"], "observed": r["observed"], "bound": r["bound"],
                     "evidence_class": r["evidence_class"]}
                    for r in requirements.values() if r["result"] in ("not_satisfied", "conflicting")]},
        {"id": "missing_measurements", "question": "Which measurements are still missing?",
         "answer": [{"requirement": r["id"], "text": r["text"]} for r in requirements.values()
                    if r["result"] == "not_measured"]
         + [{"prediction": p["id"], "quantity": p["quantity"]} for p in predictions.values() if p["result"] == "not_measured"]},
        {"id": "human_review", "question": "What needs human engineering judgement?",
         "answer": [{"requirement": r["id"], "text": r["text"]} for r in requirements.values()
                    if r["result"] == "requires_human_review"]
         + [{"discrepancy": d["id"], "next_action": d["next_action"]} for d in discrepancies if d["status"] == "open"]},
        {"id": "next_experiments", "question": "Which inert experiments are proposed next?",
         "answer": [{"preregistration": p["id"], "title": p["title"], "status": p["status"]}
                    for p in sorted(records.preregistrations.values(), key=lambda p: p["id"])]},
        {"id": "depends_on", "question": "Which claims depend on each file?",
         "answer": dict(sorted(depends.items()))},
        {"id": "refused", "question": "What does the repository refuse to claim?",
         "answer": ["Flight readiness or any live-propulsion result.",
                    "Any physical performance without a human-accepted inert measurement.",
                    "That a passing test, clean dataset, valid hash, or matching model validates hardware."]},
    ]
