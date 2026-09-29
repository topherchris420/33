"""Accessible, self-contained HTML; no CDN, remote fonts, or telemetry.

The page is an engineering review console, not a dashboard: every number is
traceable to a record, every unknown is printed as unknown, and unresolved
states are styled as normal information rather than as alarms.
"""

import base64
import hashlib
from html import escape
from urllib.parse import quote

from . import vocabulary as V

STYLE = """
:root{color-scheme:light dark;--bg:#f6f7f5;--panel:#ffffff;--line:#d9ddd8;--ink:#15201c;--muted:#5b6b64;--accent:#1f6f5a;
--open:#8a5a00;--open-bg:#fbf1dc;--bad:#9b2c2c;--bad-bg:#f8e3e1;--good:#1f6f5a;--good-bg:#e1f1ea;--none:#58616a;--none-bg:#eceff1;--focus:#b36b00}
@media (prefers-color-scheme:dark){:root{--bg:#0d1412;--panel:#131d1a;--line:#2a3a35;--ink:#e8efeb;--muted:#9fb1a9;--accent:#8fd8bb;
--open:#f0c36b;--open-bg:#2d2616;--bad:#f2a39b;--bad-bg:#321b1a;--good:#8fd8bb;--good-bg:#15291f;--none:#b6c0c7;--none-bg:#20282c;--focus:#f0c36b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--accent);text-underline-offset:3px}:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
header,main,footer{max-width:1240px;margin:auto;padding:22px 32px}header{display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid var(--line);align-items:center}
.brand{font-size:12px;letter-spacing:.14em;font-weight:700}.brand b{display:inline-grid;place-items:center;border:1px solid var(--accent);width:36px;height:36px;margin-right:12px;font-size:16px}
.stamp{font:12px ui-monospace,monospace;color:var(--muted);text-align:right;overflow-wrap:anywhere}
h1{font-size:clamp(28px,4vw,44px);line-height:1.1;letter-spacing:-.03em;font-weight:600;margin:28px 0 10px;max-width:900px}
h2{font-size:21px;letter-spacing:-.01em;margin:48px 0 6px;padding-top:12px;border-top:1px solid var(--line)}h3{font-size:19px;margin:6px 0}h4{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:18px 0 6px}
.lede{color:var(--muted);max-width:900px;font-size:16px}.sub{color:var(--muted);font-size:13px;margin:0 0 14px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden;margin:22px 0}
.stat{background:var(--panel);padding:14px 16px}.stat strong{display:block;font-size:28px;font-weight:550;line-height:1.2}.stat span{font-size:12px;color:var(--muted)}
.scopes{list-style:none;padding:0;margin:0;display:grid;gap:6px}.scopes li{display:flex;gap:12px;align-items:baseline;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:8px 12px}
.chip{display:inline-block;font:600 10.5px/1.5 system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;border-radius:4px;padding:2px 7px;border:1px solid currentColor;white-space:nowrap}
.s-open,.r-not_evaluable,.r-not_evaluated,.r-requires_human_review,.f-never_reviewed,.x-open,.st-partial{color:var(--open);background:var(--open-bg)}
.s-contradicted,.r-not_satisfied,.r-conflicting,.x-contradicts_claim,.st-failed,.c-outside_criterion,.f-source_changed,.f-statement_changed,.f-assumption_changed,.f-missing_dependency,.st-stale{color:var(--bad);background:var(--bad-bg)}
.s-supported_within_limits,.r-satisfied,.st-passed,.f-current,.x-resolved,.c-within_criterion{color:var(--good);background:var(--good-bg)}
.s-superseded,.r-not_measured,.c-not_measured,.st-not_run,.st-not_established,.st-not_assessed,.x-informational,.x-accepted_limitation,.c-no_criterion,.c-pending_acceptance,.cls{color:var(--none);background:var(--none-bg)}
.x-weakens_claim{color:var(--open);background:var(--open-bg)}
.unmeasured{font:600 11px ui-monospace,monospace;letter-spacing:.05em;color:var(--none);background:repeating-linear-gradient(135deg,var(--none-bg) 0 6px,transparent 6px 12px);border:1px dashed var(--none);padding:1px 6px;border-radius:3px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel)}table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;font-weight:600;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;background:var(--bg)}th,td{border-bottom:1px solid var(--line);padding:8px 10px;vertical-align:top}tr:last-child td{border-bottom:0}
.passport{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px 24px;margin:18px 0}.passport-head{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.cid{font:600 15px ui-monospace,monospace;color:var(--accent)}.q{color:var(--muted);font-style:italic;margin:4px 0 10px}.statement{font-size:16px;max-width:960px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 36px}ul{padding-left:18px;margin:4px 0}li{margin:3px 0}
.ladder{display:flex;gap:3px;margin:6px 0 2px;flex-wrap:wrap}.rung{font-size:10.5px;padding:3px 7px;border-radius:3px;border:1px solid var(--line);color:var(--muted)}.rung.on{border-color:var(--accent);color:var(--accent);font-weight:650}.rung.at{background:var(--accent);color:var(--panel)}
code,.mono{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.muted{color:var(--muted)}details{margin:8px 0}summary{cursor:pointer;color:var(--accent)}
.sides{display:grid;grid-template-columns:1fr 1fr;gap:10px}.side{border-left:3px solid var(--line);padding:4px 10px;font-size:13.5px}.discrepancy{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin:10px 0}
.toolbar{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0}.toolbar label{font-size:12px;color:var(--muted);display:grid;gap:4px}input,select{font:inherit;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:5px;padding:7px 10px;min-height:38px}
.note{border-left:3px solid var(--open);background:var(--open-bg);padding:10px 14px;margin:14px 0}.principles{columns:2;gap:36px}footer{border-top:1px solid var(--line);font-size:12px;color:var(--muted);margin-top:40px}
[hidden]{display:none!important}@media(max-width:760px){header,main,footer{padding:16px}.grid,.sides{grid-template-columns:1fr}.principles{columns:1}header{flex-direction:column;align-items:flex-start}.stamp{text-align:left}}
@media print{body{background:#fff;color:#000;font-size:11px}.toolbar,nav{display:none}.passport,.discrepancy{break-inside:avoid}}
"""

SCRIPT = """
const search = document.getElementById('search');
const status = document.getElementById('status');
function filterClaims() {
  const text = search.value.toLowerCase().trim();
  let shown = 0;
  document.querySelectorAll('[data-claim]').forEach(el => {
    const ok = (!status.value || el.dataset.status === status.value) && el.textContent.toLowerCase().includes(text);
    el.hidden = !ok;
    if (ok && el.classList.contains('passport')) shown += 1;
  });
  document.getElementById('results').textContent = shown + ' passports shown';
}
if (search) { search.addEventListener('input', filterClaims); status.addEventListener('change', filterClaims); }
const dstate = document.getElementById('dstate');
if (dstate) dstate.addEventListener('change', () => {
  document.querySelectorAll('.discrepancy').forEach(el => { el.hidden = dstate.value && el.dataset.state !== dstate.value; });
});
"""


def esc(value):
    return escape(str(value), quote=True)


def chip(text, css):
    return f'<span class="chip {esc(css)}">{esc(text)}</span>'


def unmeasured(text="NOT MEASURED"):
    return f'<span class="unmeasured">{esc(text)}</span>'


def lst(values, empty="None recorded."):
    if not values:
        return f'<p class="muted">{esc(empty)}</p>'
    return "<ul>" + "".join(f"<li>{esc(v)}</li>" for v in values) + "</ul>"


def table(headers, rows, cls=""):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap {cls}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def fmt(value):
    """Print a value without ever turning 'unknown' into a number."""
    if value is None:
        return '<span class="muted">none</span>'
    if isinstance(value, bool):
        return esc(str(value).lower())
    if isinstance(value, float):
        return esc(f"{value:.6g}")
    if isinstance(value, list):
        return " – ".join(fmt(v) for v in value)
    if isinstance(value, dict):
        return "<br>".join(f"{esc(k)}: {esc(v)}" for k, v in value.items())
    return esc(value)


def bound_text(bound, unit):
    if not bound:
        return '<span class="muted">none stated</span>'
    parts = []
    if "min" in bound:
        parts.append(f"≥ {bound['min']}")
    if "max" in bound:
        parts.append(f"≤ {bound['max']}")
    if "equals" in bound:
        parts.append(f"= {str(bound['equals']).lower()}")
    return esc(" and ".join(parts) + (f" {unit}" if unit and unit not in ("boolean",) else ""))


def cls_chip(key):
    return chip(V.EVIDENCE_CLASSES[key]["label"] if key in V.EVIDENCE_CLASSES else key, "cls") if key else ""


def _page(title, content, subtitle, source_line=""):
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; base-uri 'none'; form-action 'none'">
<title>{esc(title)} · Project 33</title><style>{STYLE}</style></head>
<body><header><div class="brand"><b>33</b>PROJECT 33 · EVIDENCE OBSERVATORY</div><div class="stamp">{esc(subtitle)}<br>{source_line}</div></header>
<main>{content}</main><footer>Project 33 · inert bench research · open source. Portable review artifact; no network requests.
Hash integrity does not establish physical validity.<br>
<a href="manifest.json">Manifest</a> · <a href="manifest.sha256">Manifest digest</a> · <a href="README.txt">Verification instructions</a></footer>
<script>{SCRIPT}</script></body></html>'''


def _source_line(provenance):
    commit = provenance.get("commit") or "commit unavailable"
    tree = {True: "MODIFIED working tree", False: "clean working tree", None: "working tree unknown"}[provenance.get("worktree_dirty")]
    return f"source {esc(commit[:12] if len(commit) >= 12 else commit)} · {esc(tree)}"


def _ladder(claim):
    reached = V.GATE_INDEX[claim["gate"]]
    return '<div class="ladder" aria-label="validation gates">' + "".join(
        f'<span class="rung{" on" if index <= reached else ""}{" at" if index == reached else ""}">{esc(label)}</span>'
        for index, (_, label) in enumerate(V.GATES)) + "</div>"


def _requirement_rows(results, requirements):
    rows = []
    for ref in results:
        r = requirements[ref["id"]]
        observed = r["observed"]
        if r["result"] == "not_measured":
            observed_html = unmeasured()
        elif r["result"] == "requires_human_review":
            observed_html = '<span class="muted">judgement, not a value</span>'
        elif observed is None:
            observed_html = f'<span class="muted">{esc(r["reason"] or "no value")}</span>'
        else:
            observed_html = fmt(observed)
        alternates = "".join(
            f'<br><small>{esc(a["label"])}: {fmt(a["observed"])} {chip(V.REQUIREMENT_RESULTS[a["result"]], "r-" + a["result"])}</small>'
            for a in r["alternates"])
        rows.append([f'<span class="mono">{esc(r["id"])}</span>', esc(r["text"]), esc(r["check"].replace("_", " ")),
                     bound_text(r["bound"], r["unit"]), observed_html + alternates,
                     chip(r["label"], "r-" + r["result"]) + (" " + cls_chip(r["evidence_class"]) if r["evidence_class"] else "")])
    return rows


def _prediction_rows(predictions):
    rows = []
    for p in predictions:
        if p["measurements"]:
            last = p["measurements"][-1]
            measured, abs_err = fmt(last["measured"]), fmt(last["absolute_error"])
            rel = fmt(last["relative_error"]) if last["relative_error"] is not None else '<span class="muted">not computable</span>'
        else:
            measured, abs_err, rel = unmeasured(), '<span class="muted">—</span>', '<span class="muted">—</span>'
        criterion = (f'{p["acceptance"]["type"]} ± {p["acceptance"]["tolerance"]}' if p["acceptance"]
                     else '<span class="muted">not pre-registered</span>')
        drift = f'<br>{chip("PREDICTION DRIFT", "r-not_satisfied")} {esc(p["drift"])}' if p["drift"] else ""
        rows.append([f'<span class="mono">{esc(p["id"])}</span>', esc(p["quantity"]) + f'<br><small class="muted">{esc(p["condition"])}</small>',
                     f'{fmt(p["predicted"])} {esc(p["unit"])}<br>{cls_chip(p["evidence_class"])}',
                     fmt(p["model_uncertainty"]) if p["model_uncertainty"] is not None else '<span class="muted">not quantified</span>',
                     measured, abs_err, rel, criterion, chip(p["result_label"], "c-" + p["result"]) + drift])
    return rows


def render_review(review):
    artifacts = {a["id"]: a for a in review["artifacts"]}
    requirements = {r["id"]: r for r in review["requirements"]}
    predictions = {p["id"]: p for p in review["predictions"]}
    discrepancies = {d["id"]: d for d in review["discrepancies"]}
    counts = review["counts"]

    matrix = []
    for c in review["claims"]:
        req_chips = " ".join(chip(r["id"].split("-", 2)[-1] + ": " + r["label"], "r-" + r["result"]) for r in c["requirement_results"])
        matrix.append((c, [f'<a class="cid" href="#{esc(c["id"])}">{esc(c["id"])}</a>', esc(c["title"]),
                           chip(c["status_label"], "s-" + c["status"]), chip(c["support_label"], "cls"),
                           esc(c["gate_label"]), req_chips,
                           ", ".join(f'<a href="#{esc(d)}">{esc(d)}</a>' for d in c["discrepancies_open"]) or '<span class="muted">none</span>',
                           chip(c["freshness_label"], "f-" + c["freshness"]["state"])]))
    matrix_html = '<div class="table-wrap"><table><thead><tr>' + "".join(
        f"<th>{h}</th>" for h in ("Claim", "Title", "Status", "Strongest accepted evidence", "Gate reached",
                                  "Requirements", "Open discrepancies", "Review")) + "</tr></thead><tbody>" + "".join(
        f'<tr data-claim data-status="{esc(c["status"])}">' + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for c, row in matrix) + "</tbody></table></div>"

    scopes = "".join(f'<li>{chip(s["state"].replace("_", " "), "st-" + s["state"])}<span>{esc(s["text"])}</span></li>'
                     for s in review["scopes"])

    passports = []
    for c in review["claims"]:
        sources = []
        for ref in c["evidence"]:
            a = artifacts[ref]
            rows = f" · {a['row_count']} data rows" if "row_count" in a else ""
            sources.append([f'<a href="{quote(a["snapshot_path"], safe="/")}">{esc(a["path"])}</a><br><small class="muted">{esc(a["description"])}</small>',
                            cls_chip(a["class"]), f'<code>{esc(a["sha256"][:16])}…</code><br><small class="muted">{a["bytes"]:,} bytes{rows}</small>'])
        history = "".join(f'<li><a href="{quote(artifacts[ref]["snapshot_path"], safe="/")}">{esc(artifacts[ref]["path"])}</a> — {esc(artifacts[ref]["description"])}</li>'
                          for ref in c["historical"])
        fresh = c["freshness"]
        review_line = ("No review record exists." if not fresh["review"] else
                       f'{esc(V.REVIEW_KINDS[fresh["review"]["kind"]])} Recorded {esc(fresh["review"]["recorded"])} by '
                       f'{esc(fresh["review"]["recorded_by"])}: “{esc(fresh["review"]["note"])}”')
        changed = f'<br>Changed since then: <code>{esc(", ".join(fresh["changed"]))}</code>' if fresh["changed"] else ""
        linked = [discrepancies[d] for d in c["discrepancies_open"] + c["discrepancies_resolved"]]
        disc = "".join(f'<li><a href="#{esc(d["id"])}">{esc(d["id"])}</a> {chip(V.DISCREPANCY_STATUSES[d["status"]], "x-" + d["status"])} {esc(d["title"])}</li>' for d in linked)
        preds = [predictions[p] for p in c["predictions"]]
        passports.append(f'''<article class="passport" id="{esc(c["id"])}" data-claim data-status="{esc(c["status"])}">
<div class="passport-head"><span class="cid">{esc(c["id"])}</span>{chip(c["status_label"], "s-" + c["status"])}{chip(c["support_label"], "cls")}{chip("Review: " + c["freshness_label"], "f-" + fresh["state"])}</div>
<h3>{esc(c["title"])}</h3><p class="q">Question: {esc(c["question"])}</p><p class="statement">{esc(c["statement"])}</p>
<p class="sub">{esc(c["status_meaning"])}</p>{_ladder(c)}
<h4>Requirements</h4>{table(["ID", "Requirement", "Check", "Bound", "Observed", "Result"], _requirement_rows(c["requirement_results"], requirements)) if c["requirement_results"] else '<p class="muted">No requirement linked.</p>'}
{('<h4>Predictions and measurements</h4>' + table(["ID", "Quantity", "Predicted", "Model uncertainty", "Measured", "Abs. error", "Rel. error", "Criterion", "Result"], _prediction_rows(preds))) if preds else ''}
<div class="grid"><div><h4>Known contradictions</h4>{lst(c["known_contradictions"], "None on record.")}
<h4>Open questions</h4>{lst(c["concerns"], "None recorded.")}
<h4>Measurement needed to close the next gate</h4>{lst(c["measurement_needed"])}
<h4>What this claim does not establish</h4>{lst(c["not_established"])}</div>
<div><h4>Assumptions</h4>{lst(c["assumptions"])}<h4>Limitations</h4>{lst(c["limitations"])}
<h4>Discrepancies</h4>{("<ul>" + disc + "</ul>") if disc else '<p class="muted">None linked.</p>'}
<h4>Pre-registered experiments</h4>{lst([p for p in c["preregistrations"]], "None.")}</div></div>
<h4>Evidence cited</h4>{table(["Artifact", "Class", "SHA-256"], sources)}
<details><summary>Last review, history, and change dependencies</summary><p>{review_line}{changed}</p>
{('<p>Earlier versions (superseded, kept in the failure archive):</p><ul>' + history + '</ul>') if history else ''}
<p class="muted">A change to any of these files makes the last review insufficient:</p><ul>{"".join(f"<li><code>{esc(p)}</code></li>" for p in c["affected_by_changes"])}</ul></details>
</article>''')

    trace_rows = []
    for r in review["requirements"]:
        trace_rows.append([f'<span class="mono">{esc(r["id"])}</span><br><small>{esc(", ".join(r["claims"]))}</small>',
                           esc(r["text"]) + f'<br><small class="muted">Source: {esc(r["source"])}</small>',
                           lst(r["assumptions"], "none stated"),
                           "<br>".join(f"<code>{esc(artifacts[a]['path'])}</code>" for a in r["implementation"]) or '<span class="muted">none</span>',
                           "<br>".join(f"<code>{esc(artifacts[a]['path'])}</code>" for a in r["tests"]) or '<span class="muted">none</span>',
                           esc(V.CHECK_TYPES[r["check"]]),
                           chip(r["label"], "r-" + r["result"]) + (" " + cls_chip(r["evidence_class"]) if r["evidence_class"] else "")])

    disc_html = []
    for d in review["discrepancies"]:
        sides = "".join(f'<div class="side"><strong>{esc(artifacts[s["artifact"]]["path"] if "artifact" in s else s["path"])}</strong><br>{esc(s["says"])}</div>' for s in d["sides"])
        resolution = (f'<p><strong>Resolution:</strong> {esc(d["resolution"])} <span class="muted">({esc(d["resolved_by"])})</span></p>' if d["resolution"] else "")
        progress = f'<p><strong>Progress:</strong> {esc(d["progress"])}</p>' if d.get("progress") else ""
        disc_html.append(f'''<div class="discrepancy" id="{esc(d["id"])}" data-state="{esc(d["status"])}"><div class="passport-head"><span class="cid">{esc(d["id"])}</span>
{chip(V.DISCREPANCY_STATUSES[d["status"]], "x-" + d["status"])}{chip(V.DISCREPANCY_EFFECTS[d["effect"]], "x-" + d["effect"])}<span class="muted">{esc(d["kind"].replace("_", " "))} · {esc(", ".join(d["claims"]) or "no claim")}</span></div>
<h3>{esc(d["title"])}</h3><div class="sides">{sides}</div><p><strong>Next action:</strong> {esc(d["next_action"])}</p>{progress}{resolution}
<p class="muted"><small>Found by: {esc(d["found_by"])}</small></p></div>''')

    prereg_rows = [[f'<span class="mono">{esc(p["id"])}</span>', esc(p["title"]) + f'<br><small class="muted">{esc(p["question"])}</small>',
                    chip(p["status"], "r-requires_human_review" if p["status"] == "proposed" else "r-satisfied"),
                    esc(p["prediction"]), esc(p["interpretation_rule"]),
                    esc(p["registered_by"] or "not registered by a human")] for p in review["preregistrations"]]
    archive_rows = [[f'<a href="{quote("artifacts/" + a["path"], safe="/")}">{esc(a["path"])}</a>' if a["path"] in {x["path"] for x in review["artifacts"]} else f'<code>{esc(a["path"])}</code>',
                     esc(a["kind"].replace("_", " ")), esc(a["original_path"]), esc(a["reason"]), esc(", ".join(a["discrepancies"]) or "—")]
                    for a in review["archive"]]
    violations = "".join(f'<li>{chip(v["code"].replace("_", " "), "st-failed")} {esc(v["message"])}</li>' for v in review["violations"])
    consistency_rows = [[f'<span class="mono">{esc(k["id"])}</span>', esc(k["description"]), fmt(k["left"]), fmt(k["right"]),
                         chip(k["result"], "st-passed" if k["result"] == "passed" else "st-failed")] for k in review["consistency"]]

    questions = []
    for q in review["questions"]:
        answer = q["answer"]
        if isinstance(answer, dict):
            body = "<ul>" + "".join(f"<li><code>{esc(k)}</code> → {esc(', '.join(v))}</li>" for k, v in answer.items()) + "</ul>"
        elif answer and isinstance(answer[0], dict):
            body = "<ul>" + "".join("<li>" + "; ".join(f"{esc(k)}: {fmt(v)}" for k, v in item.items()) + "</li>" for item in answer) + "</ul>"
        else:
            body = lst(answer, "None.")
        questions.append(f"<details><summary>{esc(q['question'])}</summary>{body}</details>")

    ladder_rows = [[chip(v["label"], "cls"), "yes" if v["physical"] else "no", esc(v["meaning"])] for v in V.EVIDENCE_CLASSES.values()]
    source = review["provenance"]
    content = f'''<h1>Every engineering claim should have somewhere solid to stand.</h1>
<p class="lede">{esc(review["scope"])}</p>
<div class="stats">
<div class="stat"><strong>{counts["claims"]}</strong><span>claims traced</span></div>
<div class="stat"><strong>{counts["unresolved_claims"]}</strong><span>unresolved or contradicted</span></div>
<div class="stat"><strong>{counts["requirement_results"].get("not_satisfied", 0) + counts["requirement_results"].get("conflicting", 0)}</strong><span>requirements failing or disputed</span></div>
<div class="stat"><strong>{counts["discrepancies_open"]}</strong><span>open discrepancies of {counts["discrepancies_total"]}</span></div>
<div class="stat"><strong>{counts["predictions_not_measured"]}/{counts["predictions_total"]}</strong><span>predictions not yet measured</span></div>
<div class="stat"><strong>{counts["accepted_physical_measurements"]}</strong><span>accepted inert measurements</span></div></div>
<div class="note"><p><strong>Unresolved is a valid engineering state.</strong> This packet shows what the record can support today, at the class of evidence it actually has. A model is not a measurement; a passing test is not a qualification result.</p></div>

<h2>What this packet establishes, and what it does not</h2><p class="sub">Each scope is reported on its own. There is no single "verified".</p><ul class="scopes">{scopes}</ul>

<h2>Claim status</h2><p class="sub">Support is derived from evidence classes; it cannot be authored. Gates beyond synthetic testing require human-accepted inert measurements.</p>{matrix_html}

<h2>Evidence questions</h2><p class="sub">Answers are computed from the record in this packet. Nothing here is generated prose.</p>{"".join(questions)}

<h2>Claim passports</h2>
<div class="toolbar"><label>Search passports<input id="search" type="search" placeholder="e.g. spring, synthetic, D-006"></label>
<label>Status<select id="status"><option value="">All statuses</option>{"".join(f'<option value="{k}">{esc(v[0])}</option>' for k, v in V.CLAIM_STATUSES.items())}</select></label>
<span id="results" role="status" aria-live="polite" class="muted" style="align-self:end">{len(review["claims"])} passports shown</span></div>
{"".join(passports)}

<h2>Requirement traceability</h2><p class="sub">Requirement → assumptions → implementation → tests → evaluated result, with the evidence class the result was computed from.</p>
{table(["Requirement", "Text", "Assumptions", "Implementation", "Tests", "How checked", "Result"], trace_rows)}

<h2>Prediction ledger and model-to-measurement comparison</h2><p class="sub">Predicted values are frozen at registration. An empty measurement is printed as NOT MEASURED, never as zero.</p>
{table(["ID", "Quantity", "Predicted", "Model uncertainty", "Measured", "Abs. error", "Rel. error", "Criterion", "Result"], _prediction_rows(review["predictions"]))}

<h2>Discrepancy register</h2><p class="sub">When two parts of the project disagree, the disagreement is recorded here with both sides.</p>
<div class="toolbar"><label>Show<select id="dstate"><option value="">All discrepancies</option><option value="open">Open</option><option value="resolved">Resolved</option><option value="accepted_limitation">Accepted limitation</option></select></label></div>
{"".join(disc_html)}

<h2>Pre-registered experiments</h2><p class="sub">Question, prediction, and interpretation rule written before a test. Proposed entries have not been adopted by a human.</p>
{table(["ID", "Experiment", "Status", "Prediction", "Interpretation rule", "Registered by"], prereg_rows)}

<h2>Record consistency</h2>{("<ul>" + violations + "</ul>") if violations else '<p>No drift, stale review, or failed consistency check.</p>'}
{table(["Check", "Description", "Left", "Right", "Result"], consistency_rows)}

<h2>Failure archive</h2><p class="sub">Superseded models, rejected tests, and historical claims, kept byte for byte with their digests.</p>
{table(["File", "Kind", "Originally", "Why archived", "Discrepancies"], archive_rows)}

<h2>Evidence ladder</h2><p class="sub">An artifact's class says what it can demonstrate. Evidence never promotes itself.</p>
{table(["Class", "Physical", "What it can show"], ladder_rows)}
<h4>Principles</h4><ul class="principles">{"".join(f"<li>{esc(p)}</li>" for p in review["principles"])}</ul>
<h4>Automated and AI review boundary</h4>{lst(review["ai_boundary"])}

<h2>Reproduce this review</h2><p><code>python -m evidence verify .</code> from the <code>reviewer</code> folder checks integrity offline.
From a checkout at commit <code>{esc(source.get("commit") or "unknown")}</code>: <code>python -m evidence check</code> re-evaluates the record,
<code>python -m evidence reproduce</code> regenerates model outputs, and <code>python -m pytest tests Firmware/tests</code> runs the tests.</p>
<h4>Interpretation boundary</h4>{lst(review["limitations"])}
<p><a href="assessment.json">assessment.json</a> · <a href="questions.json">questions.json</a> · <a href="records/catalog.json">records/</a></p>'''
    return _page("Evidence review", content, "OFFLINE REVIEW PACKET", _source_line(source))


def render_audit(audit):
    from .plots import telemetry_svg

    rows = [[esc(item["code"].replace("_", " ")), chip(item["severity"], "r-not_satisfied" if item["severity"] == "error" else "r-not_evaluable"),
             str(item["count"])] for item in audit["findings"]]
    stream_rows = [[esc(f"{s['source']} / {s['message_type']}"), esc(s["clock_domain"]), str(s["valid_samples"]),
                    str(s["invalid_samples"]), str(s["duplicate_samples"]), str(s["clock_regressions"]),
                    str(s["gaps_over_threshold"]),
                    fmt(s["median_positive_interval_ms"]) if s["median_positive_interval_ms"] is not None else unmeasured("NOT MEASURED"),
                    fmt(s.get("expected_interval_ms")) if s.get("expected_interval_ms") is not None else '<span class="muted">none stated</span>']
                   for s in audit["streams"]]
    dumps = [[str(d["index"]), fmt(d["announced"]), str(d["received"]), "yes" if d["terminated"] else "no",
              chip(d["state"].replace("_", " "), "st-passed" if d["state"] == "complete" else "st-failed")]
             for d in audit.get("log_dumps") or []]
    gains = [[esc(g["source"]), esc(g["kp"]), esc(g["kd"]), esc(g["first_received"]), esc(g["last_received"]), str(g["status_rows"])]
             for g in audit.get("gain_windows") or []]
    commands = [[esc(c["code"]), str(c["count"])] for c in audit.get("command_responses", [])]
    content = f'''<h1>Before the conclusion, inspect the capture.</h1>
<p class="lede">Telemetry data-quality review. Declared origin: <strong>{esc(audit["origin"])}</strong> (an operator declaration, not proof).
Live packets and recovered logs are kept separate, and each is timed by its own clock.</p><code>Input sha256 {esc(audit["input_sha256"])}</code>
<div class="stats"><div class="stat"><strong>{audit["row_count"]}</strong><span>CSV rows</span></div>
<div class="stat"><strong>{audit["invalid_rows"]}</strong><span>invalid rows</span></div>
<div class="stat"><strong>{len(audit["streams"])}</strong><span>separate streams</span></div>
<div class="stat"><strong>{esc(audit["quality"])}</strong><span>data quality</span></div></div>
<div class="note"><p>A clean capture does not establish physical performance. A gap over {esc(audit["gap_threshold_ms"])} ms is an observation, not a packet-loss count.</p></div>
<h2>Recorded signals</h2><p class="sub">Raw values as recorded. Lines break at gaps and clock regressions; invalid samples are counted in each caption and never drawn as zero.</p>
{telemetry_svg(audit.get("series", []), audit["gap_threshold_ms"])}
<h2>Quality findings</h2>{table(["Finding", "Severity", "Count"], rows) if rows else "<p>No quality findings.</p>"}
<h2>Stream integrity</h2>{table(["Stream", "Clock", "Valid", "Invalid", "Duplicates", "Clock regressions", "Gaps", "Median interval (ms)", "Expected (ms)"], stream_rows)}
<p class="muted">Intervals use positive deltas between valid samples within one stream segment.</p>
<h2>Onboard log dumps</h2>{table(["Dump", "Announced rows", "Received rows", "Terminated", "State"], dumps) if dumps else ('<p class="muted">No raw column: dump markers NOT RECORDED in this capture.</p>' if audit.get("log_dumps") is None else '<p class="muted">No LOG_START markers in this capture.</p>')}
<h2>Controller gains observed</h2>{table(["Source", "Kp", "Kd", "First seen", "Last seen", "STATUS rows"], gains) if gains else '<p class="muted">No STATUS gains observed: controller configuration is NOT RECORDED in this capture.</p>'}
<h2>Command responses in the capture</h2>{table(["Response", "Count"], commands) if commands else '<p class="muted">No command acknowledgements or rejections recorded.</p>'}
<h2>What this cannot establish</h2>{lst(audit["limitations"])}
<p><a href="audit.json">Full audit JSON</a> · <a href="telemetry.csv">Original CSV</a></p>'''
    return _page("Telemetry quality", content, f"DECLARED ORIGIN / {audit['origin'].upper()}")


def _value(value):
    if value == "NOT RECORDED":
        return unmeasured("NOT RECORDED")
    if isinstance(value, list):
        if not value:
            return '<span class="muted">none</span>'
        if isinstance(value[0], dict):
            return "<br>".join("; ".join(f"{esc(k)}: {esc(v)}" for k, v in item.items()) for item in value)
        return esc(", ".join(str(v) for v in value))
    return fmt(value)


def render_session(passport, audit):
    """A bench session passport: what was tested, with what, and what it cannot establish."""
    from .plots import telemetry_svg

    stage_css = "r-requires_human_review" if passport["stage"] == "review_candidate" else "r-not_evaluable"
    sections = []
    for title, block in (("What was tested", passport["what_was_tested"]), ("Versions", passport["versions"]),
                         ("Configuration", passport["configuration"]), ("Capture", passport["capture"])):
        rows = [[esc(key.replace("_", " ")), _value(value)] for key, value in block.items()]
        sections.append(f"<h2>{esc(title)}</h2>" + table(["Item", "Recorded"], rows))
    warnings = "".join(f'<li>{chip(w["code"].replace("_", " "), "st-failed")} {esc(w["text"])}</li>' for w in passport["warnings"])
    raw_rows = [[f'<a href="{quote("session/" + f["path"], safe="/")}">{esc(f["path"])}</a>', f'{f["bytes"]:,}', f'<code>{esc(f["sha256"])}</code>']
                for f in passport["raw_files"]]
    findings = [[esc(f["code"].replace("_", " ")), esc(f["severity"]), str(f["count"])] for f in audit["findings"]]
    content = f'''<h1>Session passport: {esc(passport["session_id"])}</h1>
<p class="lede">{chip(passport["stage"].replace("_", " "), stage_css)} {esc(passport["stage_meaning"])}</p>
<div class="stats"><div class="stat"><strong>{esc(passport["origin_declared"])}</strong><span>declared origin (not proof)</span></div>
<div class="stat"><strong>{esc(audit["quality"])}</strong><span>data quality</span></div>
<div class="stat"><strong>{len(passport["warnings"])}</strong><span>passport warnings</span></div>
<div class="stat"><strong>{esc(", ".join(passport["potentially_affected_claims"]) or "none")}</strong><span>claims this session may inform</span></div></div>
<h2>Warnings</h2>{("<ul>" + warnings + "</ul>") if warnings else '<p>None.</p>'}
{"".join(sections)}
<h2>Recorded signals</h2>{telemetry_svg(audit.get("series", []), audit["gap_threshold_ms"])}
<h2>Data-quality findings</h2>{table(["Finding", "Severity", "Count"], findings) if findings else "<p>No findings.</p>"}
<h2>Raw files</h2><p class="sub">Copied byte for byte. The declaration is a separate file; raw captures are never edited.</p>{table(["File", "Bytes", "SHA-256"], raw_rows)}
<h2>What this session cannot establish</h2>{lst(passport["cannot_establish"])}
<p><strong>Next step:</strong> {esc(passport["next_step"])}</p>
<p><a href="passport.json">passport.json</a> · <a href="audit.json">audit.json</a></p>'''
    return _page("Session passport", content, f"SESSION / {passport['stage'].upper()}")
