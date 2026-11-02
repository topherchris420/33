"""Build a source-pinned, project-only reading guide. No PDF dependency."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'lab/data/bench_manual.json'

CHAPTERS = [
    ('scope', '00', 'Scope and revision record',
     'Identify the edition, configuration and evidence class before using a technical statement.',
     ['The project is a bench-validation prototype. A model, compilation result and physical observation answer different questions.',
      'A source digest identifies the exact bytes indexed here. It does not certify their scientific validity.'],
     ['docs/PROJECT_STATUS.md', 'docs/TRACEABILITY.md', 'docs/DISCREPANCIES.md'],
     'NOTE', 'Use the current claim passports to establish what is supported, contradicted or unresolved.'),
    ('description', '01', 'Description and system relationships',
     'Follow the specimen from models and CAD to electronics, telemetry and the evidence record.',
     ['The launcher, rocket processor, sensors and dashboard have different roles. Read the architecture alongside wiring and protocol definitions.',
      'The workbench is a visualization. Missing dimensions, assembly observations and manufacturing tolerances remain unspecified.'],
     ['docs/ARCHITECTURE.md', 'docs/CAD_ASSEMBLIES.md', 'docs/WIRING.md', 'docs/PROTOCOL.md'],
     'CAUTION', 'Do not treat rendered geometry as a verified assembly or a wiring instruction.'),
    ('review', '02', 'Normal workflow: offline review',
     'Read the record and reproduce its software checks before planning a bench observation.',
     ['Inspect claim status, run the record consistency check, then build a portable review packet in a fresh output directory.',
      'Verify the packet and inspect its sources and limitations. Integrity verification establishes that bytes agree; it does not establish physical performance.'],
     ['docs/EVIDENCE_OBSERVATORY.md', 'docs/TESTING.md', 'docs/USER_GUIDE.md'],
     'NOTE', 'Commands below are documentation for an offline review, and are never executed by this page.'),
    ('abnormal', '03', 'Abnormal records and degraded information',
     'Distinguish missing information, an inferred state and a confirmed observation.',
     ['Start with the observed symptom and its source. Multiple failed units can produce the same dashboard symptom; a dependency graph cannot identify a unique physical failure.',
      'Read the degraded-mode matrix and preflight audit meanings together. SENT ONLY is not acknowledgement; INFERRED is not directly observed.'],
     ['docs/GROUND_STATUS.md', 'docs/DEGRADED_MODES.md', 'docs/BENCH_SESSIONS.md'],
     'WARNING', 'Launcher SAFE does not establish rocket IDLE. Read the recorded restart limitation in the safety checklist and discrepancy D-025.'),
    ('instruments', '04', 'Instruments, displays and data quality',
     'Keep origin, units, time, validity and configuration visible beside a value.',
     ['Live telemetry and recovered onboard logs use different clock domains and must remain distinguishable. Gaps and invalid samples are part of the record.',
      'A requested gain and a gain observed in telemetry are different facts. Calibration being sent does not prove calibration completed.'],
     ['docs/GROUND_STATUS.md', 'docs/PROTOCOL.md', 'docs/BENCH_SESSIONS.md', 'docs/USB_BENCH_MONITOR.md'],
     'CAUTION', 'Missing or stale data must not be displayed as a fresh zero or an affirmative readiness state.'),
    ('limits', '05', 'Limitations and unresolved claims',
     'Locate the requirement, evidence class and open disagreement behind a result.',
     ['The claim passports and discrepancy register are the authority for model disagreements and unmet requirements. Reading this guide changes no claim.',
      'Aircraft operating limits do not define the limits of Project 33. Flight characteristics, weather qualification and flight performance are not established by this guide.'],
     ['docs/TRACEABILITY.md', 'docs/DISCREPANCIES.md', 'docs/RELEASE_READINESS.md', 'docs/SAFETY.md'],
     'WARNING', 'No checklist completion, simulation or clean software run authorizes flight or live propulsion.'),
    ('configuration', '06', 'Configuration and observation planning',
     'Bind a proposed observation to a specimen, software identity and interpretation rule.',
     ['Record specimen identity and installed binary digests; a source revision alone does not identify the binary installed on a board.',
      'Read the quantity and instrument provenance requirements. Proposed experiments need human registration before measurement; blanks remain unknown.'],
     ['docs/BENCH_CONFIGURATION.md', 'docs/ROADMAP.md', 'docs/BOM.md'],
     'NOTE', 'This guide is a reading aid. Its personal reading marks are not test records or approvals.'),
    ('sessions', '07', 'Session record and independent review',
     'Keep raw capture, declaration, audit and human acceptance separate.',
     ['Preserve raw telemetry, session metadata and command logs. Corrections belong in declarations or new sessions, not overwritten capture files.',
      'A passport can become a REVIEW CANDIDATE. Only a named human can accept a session; only accepted evidence can support physical measurements.'],
     ['docs/BENCH_SESSIONS.md', 'docs/BENCH_CONFIGURATION.md', 'docs/EVIDENCE_OBSERVATORY.md'],
     'CAUTION', 'A declared bench origin is a statement, not proof that hardware was present.'),
    ('foldouts', '08', 'Foldouts and reference index',
     'Open the architecture, dependency matrix and traceability record as companion views.',
     ['Use the architecture for system relationships, degraded modes for dependency assumptions, and traceability for claims and requirements.',
      'Consult the original project source when a summary is insufficient. This index contains no aircraft-specific procedures, diagrams or operating values.'],
     ['docs/ARCHITECTURE.md', 'docs/DEGRADED_MODES.md', 'docs/TRACEABILITY.md', 'docs/LIVING_LAB.md', 'docs/TECHNOLOGY_INTEGRATION.md', 'docs/HARDWARE_INTEGRATION_PLAN.md'],
     'NOTE', 'The source index below pins every referenced document to its SHA-256 digest.'),
]

GLOSSARY = {
    'RAW SESSION': 'Capture plus metadata; not yet accepted evidence.',
    'REVIEW CANDIDATE': 'A passport meeting the documented prerequisites for human review; not acceptance.',
    'OBSERVED': 'The recording contains the expected trace; it does not prove correct, safe or ordered execution.',
    'INFERRED': 'A conclusion implied by firmware logic rather than a directly reported state.',
    'DECLARED': 'A statement supplied by a person, not independently checked by the audit.',
    'SENT ONLY': 'A command was sent without a visible result; delivery and completion remain unknown.',
    'NOT OBSERVED': 'The recording could contain this trace but does not.',
    'CONTRADICTED': 'The recording contains something inconsistent with the checklist condition.',
    'OPERATOR ONLY': 'Packets cannot establish this condition; it requires human confirmation.',
    'NOT MEASURED': 'No accepted physical measurement is supplied; this is not a value of zero.',
}

CHECKLISTS = {
    'scope': ['Identify the source edition and configuration.', 'Read the claim status and evidence class.', 'Locate open discrepancies before interpreting a result.'],
    'description': ['Locate each subsystem in the architecture.', 'Compare wiring and protocol documents for the same configuration.', 'Separate CAD/model intent from physical assembly observations.'],
    'review': ['Inspect the output of evidence status.', 'Read findings from evidence check; retain unresolved findings.', 'Build into a new directory and verify the resulting packet.', 'Read packet limitations before citing a result.'],
    'abnormal': ['Identify the missing or stale stream and its clock domain.', 'List all model-consistent failure explanations.', 'Compare the audit label with its glossary definition.', 'Retain ambiguous or unobserved conditions as unresolved.'],
    'instruments': ['Identify the origin, units and age of the value.', 'Separate T and LOG streams.', 'Compare commanded configuration with observed configuration.', 'Check gaps, invalid samples and restart advisories.'],
    'limits': ['Locate the requirement and its evidence class.', 'Read disputed and unmet requirements.', 'Check release blockers and human-review requirements.'],
    'configuration': ['Identify the specimen and installed binary digests.', 'Locate the human-registered pre-registration.', 'Check quantity semantics, instrument identity and calibration provenance.', 'Preserve the frozen plan used for the observation.'],
    'sessions': ['Check raw files and clean-close metadata.', 'Read the declaration without modifying raw capture.', 'Read audit findings and passport limitations.', 'Distinguish a review candidate from named human acceptance.'],
    'foldouts': ['Open the system architecture.', 'Read the degraded-mode matrix assumptions.', 'Follow a claim through its source and requirement references.'],
}

TROUBLESHOOTING = [
    {'symptom': 'Launcher reports; rocket telemetry is absent',
     'interpretation': 'UART, rocket processor and an IMU failure at boot can look alike from passive packets.',
     'review': 'Inspect the status board explanations and any already-recorded log-dump response. A response narrows the model; silence does not identify one failed unit.',
     'source': 'docs/GROUND_STATUS.md'},
    {'symptom': 'Launcher state says NOT REPORTED',
     'interpretation': 'The current protocol has no launcher state message. A READY label may be an inference.',
     'review': 'Keep the inferred launcher state separate from the reported rocket state and its age.',
     'source': 'docs/GROUND_STATUS.md'},
    {'symptom': 'Gains are UNCONFIRMED or NO MATCH',
     'interpretation': 'Only later STATUS telemetry confirms a requested change. Missing telemetry is UNCONFIRMED; a differing report is NO MATCH.',
     'review': 'Compare command timestamps with subsequent STATUS records. Do not treat sending a command as confirmation.',
     'source': 'docs/GROUND_STATUS.md'},
    {'symptom': 'Calibration was sent but no change was seen',
     'interpretation': 'Firmware sends no acknowledgement and reported skew is rounded. No visible change proves neither completion nor failure.',
     'review': 'Read the calibration status and recorded skew changes; retain uncertainty in the session interpretation.',
     'source': 'docs/GROUND_STATUS.md'},
    {'symptom': 'Launcher SAFE after abort; rocket remains ARMED',
     'interpretation': 'The current implementation has no rocket disarm path through launcher abort. This is the documented D-025 limitation.',
     'review': 'Read the safety warning and the existing human-operated restart procedure. Do not interpret the launcher label as the rocket state.',
     'source': 'docs/SAFETY.md'},
    {'symptom': 'Passport does not reach REVIEW CANDIDATE',
     'interpretation': 'Required declarations or metadata may be missing, or the audit may contain errors.',
     'review': 'Inspect the passport findings, operator, purpose, inert configuration and audit. Preserve raw files and record corrections in the declaration.',
     'source': 'docs/BENCH_SESSIONS.md'},
    {'symptom': 'Evidence check reports a stale review',
     'interpretation': 'A dependency or claim statement changed. The earlier review no longer covers the current record.',
     'review': 'Inspect the changed sources and affected claim. A tooling snapshot is distinct from a human review and cannot accept physical evidence.',
     'source': 'docs/EVIDENCE_OBSERVATORY.md'},
]

def build():
    chapters = [dict(zip(('id', 'number', 'title', 'summary', 'paragraphs', 'sources', 'notice_level', 'notice'), row)) for row in CHAPTERS]
    for chapter in chapters:
        chapter['checklist'] = CHECKLISTS[chapter['id']]
        if chapter['id'] == 'abnormal':
            chapter['troubleshooting'] = TROUBLESHOOTING
            chapter['sources'] = sorted(set(chapter['sources']) | {t['source'] for t in TROUBLESHOOTING})
        if chapter['id'] == 'description':
            chapter['paragraphs'] = chapter['paragraphs'] + [
                'Rocket processor: the ESP32 reads the MPU6050 and exposes state and telemetry. Its embedded behavior is described in the architecture; compilation alone does not verify behavior on a board.',
                'Launcher: the ground ESP32 connects the rocket UART path to the dashboard and hosts launcher sensors and physical interlocks.',
                'Dashboard: captures telemetry and command history into a raw session. The separate status board interprets those records without sending commands.',
                'Evidence Observatory: binds claims to sources, requirements, discrepancies and accepted records. It provides review packets rather than hardware control.'
            ]
    paths = sorted({p for c in chapters for p in c['sources']})
    sources = [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in paths]
    payload = {'schema_version': 1, 'title': 'V3D-TO-33-1 / Utility Bench Manual',
               'scope': 'Project-only reading guide; no operational authority.',
               'chapters': chapters, 'glossary': GLOSSARY, 'sources': sources}
    payload['revision'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return json.dumps(payload, indent=2, ensure_ascii=False) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = build()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != text:
            print('Bench manual index is stale: run python tools/build_bench_manual.py')
            return 1
        print('Bench manual source index is current.')
    else:
        OUTPUT.write_text(text, encoding='utf-8')
        print('Wrote lab/data/bench_manual.json')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
