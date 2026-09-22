"""Accessible, self-contained HTML; no CDN, remote fonts, or telemetry."""

import base64
import hashlib
from html import escape
from urllib.parse import quote


STYLE = """
:root{color-scheme:dark;--bg:#081211;--panel:#10211f;--line:#29413b;--ink:#edf4ef;--muted:#a9bcb4;--mint:#b4edd1;--amber:#ffd393}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,-apple-system,sans-serif}
a{color:var(--mint);text-underline-offset:4px}a:hover{color:white}button,input,select{font:inherit}
:focus-visible{outline:3px solid var(--amber);outline-offset:4px}header,main,footer{max-width:1180px;margin:auto;padding:28px 36px}
header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);gap:20px}
.brand{font-size:13px;letter-spacing:.12em;font-weight:750}.brand span{display:inline-grid;place-items:center;border:1px solid var(--mint);width:42px;height:42px;margin-right:14px;font-size:19px}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--mint)}.stamp{color:var(--muted);font-size:12px;text-align:right}
.hero{padding:42px 0 28px}.hero h1{font-size:clamp(36px,5.5vw,68px);line-height:1.05;letter-spacing:-.055em;max-width:780px;margin:18px 0 22px;font-weight:550}
.hero p{max-width:790px;color:var(--muted);font-size:18px}.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);border-radius:12px;margin:20px 0 32px;overflow:hidden}
.stat{padding:22px;border-right:1px solid var(--line)}.stat:last-child{border:0}.stat strong{display:block;font-size:36px;line-height:1.2;font-weight:500}.stat span{font-size:12px;color:var(--muted)}
.note{border-left:3px solid var(--amber);background:#24271c;padding:18px 22px;margin:24px 0;color:#efe4ce}.note p{margin:0}
.section-title{display:flex;justify-content:space-between;gap:20px;align-items:baseline;margin-top:42px}.section-title h2{font-size:25px;letter-spacing:-.025em}.section-title span{font-size:12px;color:var(--muted)}
.toolbar{display:flex;gap:18px;flex-wrap:wrap;margin:12px 0 24px}.toolbar label{font-size:12px;color:var(--muted);display:grid;gap:6px}.toolbar label:first-child{flex:1;min-width:200px}
input,select{background:var(--panel);color:var(--ink);border:1px solid #4e6b61;padding:10px 14px;border-radius:5px;min-height:46px}
.claim{border-top:1px solid var(--line);padding:28px 0}.claim-head{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.claim-id{font:16px ui-monospace,monospace;color:var(--mint)}
.claim h3{font-size:25px;font-weight:550;margin:10px 0}.claim>p{max-width:920px}.badge{font-size:11px;text-transform:uppercase;letter-spacing:.07em;border:1px solid #476158;border-radius:20px;padding:3px 10px;color:var(--mint)}
.badge.unresolved{border-color:#937650;color:var(--amber)}.claim-grid{display:grid;grid-template-columns:1.1fr 1fr;gap:36px}.claim h4{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:8px}
ul{padding-left:20px}li{margin:6px 0}.sources{list-style:none;padding:0}.sources li{padding:8px 0;border-bottom:1px solid #20342e}.sources small{display:block;color:var(--muted)}
details{margin:18px 0}summary{cursor:pointer;color:var(--mint);padding:5px 0}code{font:12px ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted)}
.bar{height:8px;border-radius:8px;background:var(--mint);margin:7px 0 16px}.basis{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;font-size:13px;color:var(--muted)}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:var(--muted);font-weight:500}th,td{border-bottom:1px solid var(--line);padding:12px 14px 12px 0;vertical-align:top}
.muted{color:var(--muted)}.empty{padding:24px;color:var(--amber)}footer{border-top:1px solid var(--line);font-size:12px;color:var(--muted);padding-bottom:42px}
[hidden]{display:none!important}@media(max-width:650px){header,main,footer{padding:20px}.stamp{max-width:125px}.hero{padding-top:24px}.stats{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border:0}.stat:nth-child(-n+2){border-bottom:1px solid var(--line)}.claim-grid{grid-template-columns:1fr;gap:8px}.basis{grid-template-columns:repeat(2,1fr)}.section-title{display:block}}
@media print{body{background:white;color:#111}header,main,footer{max-width:none;padding:16px}a,.muted,code,li,summary{color:#222}.toolbar{display:none}.note{background:#eee;color:#111}.claim{break-inside:avoid}.hero h1{font-size:38px}.stats{margin:12px 0}.stat strong{font-size:25px}}
"""

SCRIPT = """
const search = document.getElementById('search');
const basis = document.getElementById('basis');
const state = document.getElementById('state');
function filterClaims() {
  const text = search.value.toLowerCase().trim();
  let visible = 0;
  document.querySelectorAll('.claim').forEach(claim => {
    const show = (!basis.value || claim.dataset.basis === basis.value) &&
      (!state.value || claim.dataset.state === state.value) &&
      claim.textContent.toLowerCase().includes(text);
    claim.hidden = !show;
    if (show) visible += 1;
  });
  document.getElementById('results').textContent = visible + ' claims shown';
  document.getElementById('empty').hidden = visible !== 0;
}
if (search) {
  search.addEventListener('input', filterClaims);
  basis.addEventListener('change', filterClaims);
  state.addEventListener('change', filterClaims);
}
"""


def _escape(value):
    return escape(str(value), quote=True)


def _list(values):
    return "<ul>" + "".join(f"<li>{_escape(value)}</li>" for value in values) + "</ul>"


def _stats(values):
    return '<div class="stats">' + "".join(
        f'<div class="stat"><strong>{_escape(value)}</strong><span>{_escape(label)}</span></div>'
        for value, label in values) + "</div>"


def _page(title, content, subtitle):
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; base-uri 'none'; form-action 'none'">
<title>{_escape(title)} · Project 33</title><style>{STYLE}</style></head>
<body><header><div class="brand"><span>33</span>VERS3DYNAMICS</div><div class="stamp">EVIDENCE OBSERVATORY<br>{_escape(subtitle)}</div></header>
<main>{content}</main><footer>Project 33 · Inert bench research · Open source<br>
Portable review artifact. No network requests. Hash integrity does not establish physical validity.<br>
<a href="manifest.json">Manifest</a> · <a href="manifest.sha256">Manifest digest</a> · <a href="README.txt">Verification instructions</a></footer>
<script>{SCRIPT}</script></body></html>'''


def render_review(review):
    artifacts = {item["id"]: item for item in review["artifacts"]}
    cards = []
    for claim in review["claims"]:
        sources = []
        for ref in claim["evidence"]:
            item = artifacts[ref]
            rows = f" · {item['row_count']} data rows" if "row_count" in item else ""
            sources.append(f'<li><a href="{quote(item["snapshot_path"], safe="/")}">{_escape(item["path"])}</a>'
                           f'<small>{_escape(item["kind"])} · {item["bytes"]:,} bytes{rows}</small>'
                           f'<code>sha256 {_escape(item["sha256"])}</code></li>')
        concern = ('<div class="note"><strong>Open review question</strong>'
                   + _list(claim["concerns"]) + '</div>') if claim["concerns"] else ''
        cards.append(f'''<article class="claim" id="{_escape(claim['id'])}" data-basis="{_escape(claim['basis'])}" data-state="{_escape(claim['review_state'])}">
<div class="claim-head"><span class="claim-id">{_escape(claim['id'])}</span><span class="badge">{_escape(claim['basis'])} basis</span>
<span class="badge {_escape(claim['review_state'])}">{_escape(claim['review_state'])}</span></div>
<h3>{_escape(claim['title'])}</h3><p>{_escape(claim['statement'])}</p>{concern}
<div class="claim-grid"><div><h4>What limits the claim</h4>{_list(claim['limitations'])}<h4>Next evidence needed</h4>{_list(claim['next_evidence'])}</div>
<div><h4>Inspect the evidence</h4><ul class="sources">{''.join(sources)}</ul></div></div>
<details><summary>Assumptions behind this claim</summary>{_list(claim['assumptions'])}</details></article>''')
    source = review["provenance"]
    commit = source["commit"] or "unavailable"
    state = {True: "modified working tree", False: "clean working tree", None: "working tree unknown"}[source["worktree_dirty"]]
    counts = review["basis_counts"]
    bars = ''.join(f'<div>{_escape(kind.title())} · {count}<div class="bar" style="width:{100 * count / len(cards):.2f}%"></div></div>'
                   for kind, count in counts.items())
    content = f'''<section class="hero"><div class="eyebrow">Research that can be inspected</div>
<h1>Every claim.<br>An inspectable trail.</h1><p>{_escape(review['scope'])}</p>
<code>Source { _escape(commit) } · {_escape(state)}</code></section>
{_stats([(len(cards), 'claims traced'), (len(artifacts), 'artifacts captured'), (review['physical_evidence_count'], 'declared physical artifacts'), (review['unresolved_claim_count'], 'unresolved claims')])}
<div class="note"><p><strong>Evidence availability is not validation.</strong> Classifications are authored declarations. This report checks artifact structure and preserves source bytes; it does not run the engineering models or demonstrate hardware performance.</p></div>
<div class="section-title"><h2>Evidence composition</h2><span>Declared basis of each claim</span></div><div class="basis">{bars}</div>
<div class="section-title"><h2>Follow a claim</h2><span id="results" role="status" aria-live="polite">{len(cards)} claims shown</span></div>
<div class="toolbar"><label>Search claims, gaps, and sources<input id="search" type="search" placeholder="e.g. synthetic, C7, physical"></label>
<label>Evidence basis<select id="basis"><option value="">All evidence</option><option>analytical</option><option>software</option><option>synthetic</option><option>physical</option></select></label>
<label>Review state<select id="state"><option value="">All claims</option><option>unresolved</option><option>limited</option></select></label></div>
<noscript><p>All claims remain available with JavaScript disabled.</p></noscript>
<p class="empty" id="empty" hidden>No claims match. Clear the search or filters.</p>{''.join(cards)}
<div class="section-title"><h2>Interpretation boundary</h2><a href="assessment.json">Machine-readable assessment</a></div>{_list(review['limitations'])}'''
    return _page("Evidence review", content, "OFFLINE / SOURCE-TRACEABLE")


def render_audit(audit):
    rows = ''.join(f'<tr><td>{_escape(item["code"])}</td><td>{_escape(item["severity"])}</td><td>{item["count"]}</td></tr>'
                   for item in audit["findings"])
    stream_rows = ''.join('<tr>' + ''.join(f'<td>{_escape(value)}</td>' for value in (
        f"{item['source']} / {item['message_type']}", item['valid_samples'], item['invalid_samples'],
        item['duplicate_samples'], item['clock_regressions'], item['gaps_over_threshold'],
        item['median_positive_interval_ms'] if item['median_positive_interval_ms'] is not None else 'not measured')) + '</tr>'
        for item in audit['streams'])
    content = f'''<section class="hero"><div class="eyebrow">Recorded data, examined</div><h1>Before the conclusion,<br>inspect the capture.</h1>
<p>Telemetry quality review. Declared origin: <strong>{_escape(audit['origin'])}</strong>. Live packets and recovered logs remain separate.</p><code>Input sha256 {_escape(audit['input_sha256'])}</code></section>
{_stats([(audit['row_count'], 'CSV rows'), (audit['invalid_rows'], 'invalid rows'), (len(audit['streams']), 'separate streams'), (audit['quality'], 'data quality')])}
<div class="note"><p>Origin is supplied by the operator. A clean capture does not establish physical performance. A gap over {_escape(audit['gap_threshold_ms'])} ms is an observation, not a measured packet-loss count.</p></div>
<div class="section-title"><h2>Quality findings</h2><a href="audit.json">Full audit JSON</a></div><div class="table-wrap"><table><thead><tr><th>Finding</th><th>Severity</th><th>Count</th></tr></thead><tbody>{rows or '<tr><td colspan="3">No quality findings</td></tr>'}</tbody></table></div>
<div class="section-title"><h2>Stream integrity</h2><a href="telemetry.csv">Original CSV</a></div><div class="table-wrap"><table><thead><tr><th>Stream</th><th>Valid</th><th>Invalid</th><th>Duplicates</th><th>Clock regressions</th><th>Gaps</th><th>Median interval (ms)</th></tr></thead><tbody>{stream_rows}</tbody></table></div>
<p class="muted">Intervals use positive deltas between valid samples within one stream segment. Duplicates remain visible in the sample count.</p>
<div class="section-title"><h2>What this cannot establish</h2></div>{_list(audit['limitations'])}'''
    return _page("Telemetry quality", content, f"DECLARED ORIGIN / {audit['origin'].upper()}")
