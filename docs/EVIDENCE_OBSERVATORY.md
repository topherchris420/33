# Evidence Observatory

Every engineering claim should have somewhere solid to stand. The Observatory (`evidence/`, Python 3.11+ standard library, fully offline) keeps Project 33's claims, the exact artifacts behind them, the class of evidence those artifacts are, the requirements they meet or miss, the predictions still waiting for a measurement, and every known disagreement in one checked record. It never opens a network connection, talks to hardware, or sends a command.

<!-- evidence:counts -->
**Record state:** 8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements · 17 open discrepancies of 24 · 5 of 5 predictions not measured.
<!-- /evidence:counts -->

## Principles the tooling enforces

- If the repository says it happened, point to the artifact.
- A model is not a measurement. A clean dataset is not proof of a physical event. A passing test is not a qualification result.
- Unknown is not zero. Missing is not false. Unmeasured is not passed.
- Unresolved is a valid engineering state.
- Evidence never promotes itself: support is derived from evidence classes, and the build refuses a record that claims more than its evidence shows.

## Vocabulary

### Evidence ladder (artifact classes)

| Class | Physical | What it can show |
|---|---|---|
| SPECIFICATION | no | Authored requirement, boundary, note, or historical claim. States intent; demonstrates nothing. |
| IMPLEMENTATION | no | Source, CAD source, model input, configuration. What was built, not how it behaves. |
| TEST PROCEDURE | no | Test source. A procedure, not a record that it ran. |
| SYNTHETIC | no | Fabricated data that exercises tooling. Never supports a physical claim; must identify itself in-band when it can. |
| ANALYTICAL / SIMULATED | no | Model output. Only as good as its formulation and inputs. |
| SOFTWARE VERIFIED | no | An attached execution record of automated checks (JUnit XML). Never cataloged; attached at build time. |
| BENCH OBSERVED | yes | Inert observation without calibrated measurement. Counts only via a human-accepted session. |
| BENCH MEASURED | yes | Inert measurement with instrument, calibration, and uncertainty. Counts only via a human-accepted session. |

`physical`, `verified`, `field_measured`, and `flight` are refused as classes. Field and flight data are outside the validation boundary.

### Claim status (authored, validated)

| Status | Meaning | Rule the build enforces |
|---|---|---|
| UNRESOLVED (`open`) | An open question, conflict, or missing measurement blocks a stronger statement | Something on record must be open |
| CONTRADICTED | Evidence contradicts the claim or a requirement | A requirement fails or an open discrepancy contradicts it |
| SUPPORTED WITHIN STATED LIMITS | Evidence supports the statement as worded, at its class only | No concerns, no failing or disputed requirement, no contradicting discrepancy — otherwise **no report is built** |
| SUPERSEDED | Replaced; kept for history | Names its successor |

### Derived support level

The strongest rung the claim's *accepted* evidence reaches: NO SUPPORTING EVIDENCE, IMPLEMENTATION ONLY, MODEL ONLY, SOFTWARE VERIFIED, BENCH OBSERVED, BENCH MEASURED, INDEPENDENTLY REVIEWED. It cannot be written in the catalog.

### Validation gates

ANALYTICAL MODEL → SOFTWARE REPRODUCTION → SYNTHETIC TEST → INERT BENCH SETUP → INERT PHYSICAL MEASUREMENT → REPEATED MEASUREMENT → INDEPENDENT REVIEW.

A claim's authored gate may not exceed what its records show. INERT BENCH SETUP needs a pre-registration registered by a named human; INERT PHYSICAL MEASUREMENT needs a measurement from a human-accepted session; REPEATED MEASUREMENT needs two accepted sessions whose raw bytes differ (the same file twice is one measurement); INDEPENDENT REVIEW needs a current human review marked independent.

### Requirement checks and results

| Check | Closed by | Possible results |
|---|---|---|
| machine | A committed artifact value against a bound | SATISFIED / NOT SATISFIED (with the evidence class of the value), MODELS DISAGREE when an alternate model on record disagrees, NOT EVALUABLE when no value exists |
| test | An attached execution record naming the tests | SATISFIED (software verified), NOT SATISFIED, NOT EVALUATED IN THIS BUILD (skipped is not passed) |
| human_review | Engineering judgement | REQUIRES HUMAN REVIEW |
| physical_measurement | An accepted inert measurement | NOT MEASURED until one exists |

### Review freshness

Each claim has a last review record in `evidence/reviews.json`: a digest of its wording, of its assumptions and linked requirements, predictions, and discrepancies, and of every file it depends on (closed over `derived_from`). The current state is CURRENT, NEVER REVIEWED, SOURCE CHANGED, STATEMENT CHANGED, ASSUMPTION CHANGED, or MISSING DEPENDENCY. A change makes the previous review insufficient; it never makes the claim false. `snapshot` records are tooling records that detect change; `human` records name a reviewer.

## Record files

| File | Holds |
|---|---|
| `evidence/catalog.json` | Artifacts (path, class, format, dependencies), model reproduction recipes, numerical consistency checks, and claims (the passport fields) |
| `evidence/requirements.json` | Requirements with check type, bound, value extractor, assumptions, implementation, and tests |
| `evidence/predictions.json` | Predictions frozen at registration, with model uncertainty (null = not quantified) and acceptance criterion |
| `evidence/measurements.json` | Inert measurements; each needs a human-accepted session, instrument, and uncertainty. Empty today. |
| `evidence/sessions.json` | Bench sessions promoted beyond a local raw capture, with raw-file digests. Empty today. |
| `evidence/preregistrations.json` | Question, prediction, variables, interpretation rule, and method written before a test |
| `evidence/discrepancies.json` | Every recorded mismatch, both sides, effect, status, and next action |
| `evidence/reviews.json` | Last review of each claim and its history |
| `evidence/archive/index.json` | The failure archive: superseded models, rejected tests, historical notes, each with its digest |
| `evidence/safety_gates.json` | Every interlock with the exact source text that implements it |

Human-readable views are generated from these files and checked for staleness: [claim passports](claims/README.md), [traceability](TRACEABILITY.md), the [discrepancy register](DISCREPANCIES.md), and marked fragments inside README, index, status, paper alignment, safety, and BOM.

## Commands

```bash
python -m evidence status                        # per-claim status, requirement results, scopes
python -m evidence check                         # strict: exit 1 on drift, stale reviews, failed consistency, stale docs
python -m evidence build --output build/review   # portable review packet (never overwrites)
python -m evidence verify build/review [--expected-sha256 DIGEST]
python -m evidence compare build/review build/review-02
python -m evidence drift build/review            # files changed since a packet was built, and what they affect
python -m evidence impact PATH [PATH ...]        # claims, requirements, predictions, discrepancies, checks to rerun
python -m evidence query [QUESTION_ID]           # grounded evidence questions
python -m evidence snapshot --claims C1 --note "why" [--reviewer "Your Name" [--independent]]
python -m evidence docs [--check]                # regenerate or check generated documents
python -m evidence reproduce [--only RECIPE] [--record FILE]   # needs model dependencies
python -m evidence audit CSV --origin bench --output DIR
python -m evidence session declare|passport|register|accept ...
python -m evidence demo --output build/demo      # explicitly synthetic fault example
```

`make review` builds and verifies a packet; `make check` runs the strict record check; `make review-full` attaches the pytest run record and a model-reproduction record.

## What a packet establishes

Every packet states each scope separately, in `index.html`, `README.txt`, and `assessment.json`:

| Scope | Meaning |
|---|---|
| BUNDLE INTEGRITY | Every file matches the manifest; re-check with `verify`. A digest is not a signature. |
| RECORD SCHEMA VALID | Every record file parsed and cross-referenced |
| RECORD CONSISTENCY | No prediction drift, stale review, failed consistency check, or missing value |
| REQUIREMENTS | How many were machine-evaluated, and how many need human review or physical measurement |
| SOFTWARE TESTS | Passed/failed from an attached execution record, or NOT RUN BY THIS BUILD |
| MODEL REPRODUCTION | From an attached reproduction record; STALE if the artifacts changed since |
| FIRMWARE BUILD | Not run by the packet builder (CI job); compiling is not hardware behavior |
| PHYSICAL PERFORMANCE | NOT ESTABLISHED unless accepted inert measurements exist |
| FLIGHT READINESS | NOT ASSESSED; outside the validation boundary |

Packet contents: `records/` (every record file as committed), `artifacts/` (byte copies of every cited file), `assessment.json`, `questions.json`, optional `execution/`, `reviewer/` (the verifier), `manifest.json`, `manifest.sha256`, `index.html`, `README.txt`. Given identical inputs, reviewer code, Python version, and tree state, packets are byte-identical: no wall-clock time, absolute path, or hash-seed-dependent ordering enters them.

## Predictions, measurements, and pre-registration

A prediction records a quantity, unit, condition, value, model uncertainty, the artifact it came from, and optionally an acceptance criterion. Its value is frozen: if the source artifact later reports something else, `check` fails with PREDICTION DRIFT. Register a new prediction and supersede the old one; never retune a model silently after seeing a result.

A measurement enters the record only from a human-accepted session and must carry an instrument, a method, and, for BENCH MEASURED, a calibration and an uncertainty. The comparison reports predicted value, measured value, absolute and relative error (not computable against a zero prediction), the criterion, and WITHIN CRITERION, OUTSIDE CRITERION, NO PRE-REGISTERED CRITERION, or NOT MEASURED.

A pre-registration fixes the question, prediction, variables, interpretation rule, and method before testing. Software may draft one (`proposed`); only a named human sets it to `registered`. A measurement cites the pre-registration and the fingerprint of the rule it was judged against, so a rule edited after the result, or a measurement dated before registration, is refused.

## Telemetry audits and session passports

`audit` checks a recorded dashboard CSV without connecting to hardware:

| Check | Interpretation |
|---|---|
| Non-finite or malformed sample | Error; counted and excluded, never replaced with zero |
| Device timestamp outside uint32 | Error |
| Receive timestamp without timezone | Error |
| Same device timestamp, different values | Error: conflicting evidence |
| Exact repeat at the same timestamp | Warning; retained and counted |
| Decreasing device timestamp | Warning; new segment, no cause inferred |
| Positive interval above threshold | Warning; not a packet-loss count |
| Median interval unlike the firmware period | Warning (`interval_differs_from_expected`) |
| Log dump shorter than announced, or never terminated | Warning: partial capture |
| LOG rows outside a LOG_START/LOG_END pair | Warning |
| No valid telemetry / undeclared origin | Error / warning |

Streams are separated by source and message type, and each is labeled with its clock: live `T` rows carry the **launcher's relay time**, recovered `LOG` rows the **rocket's sample time** (D-018). The audit also reports controller-gain windows seen in STATUS rows and every CMD_REJECT, CMD_ACK, and ABORT line. Its HTML plots raw values with units, breaks lines at gaps and clock regressions, and captions how many invalid samples were excluded.

A **session passport** (`session passport SESSION_DIR`) adds what the dashboard recorded (`session.json`: capture times, dashboard and protocol digests, clean close; `commands.csv`: every command sent) and the operator's separate `declaration.json` (purpose, origin, hardware and firmware revision, inert configuration, equipment, calibration). Anything not recorded is printed as NOT RECORDED, and the passport lists what the session cannot establish and which claims it might inform.

Ingestion is deliberately conservative:

**RAW SESSION → AUDITED → REVIEW CANDIDATE → HUMAN-ACCEPTED → claim review.** A passport reaches REVIEW CANDIDATE only with a bench declaration, operator, purpose, inert configuration, and no audit errors. `session register` copies the raw bytes into `evidence/sessions/` and records their digests. `session accept --reviewer NAME` is the only way to reach HUMAN-ACCEPTED. Clean data quality is necessary, never sufficient.

## Change impact and staleness

`impact PATH` follows `derived_from` to every downstream artifact and lists the claims whose reviews are no longer sufficient, the requirements and predictions that read the file, the discrepancies that cite it, the generated documents that will be stale, and the checks to rerun (reproduction recipes, tests, firmware builds, protocol check). `drift PACKET` does the same against a packet built earlier. `compare A B` reports changed files, changed artifact records, requirement result changes, claim status changes, and discrepancy changes between two packets.

## Discrepancies and the failure archive

Two parts of the project disagreeing is information. Each discrepancy names both sides (artifact or path, and what each says), the claims it affects, whether it contradicts or weakens them, and the next action. Resolved entries stay, with what resolved them; a record correction is not an engineering review.

Superseded model outputs, rejected tests, prior models, and historical claim text live in `evidence/archive/` with their SHA-256 in `index.json`. The archive is append-only: any edit to an archived file stops every build.

## Automated and AI-assisted review

Structured records exist so that people and increasingly capable tools can review quickly. The boundary is fixed:

- Tools, including AI assistants, may summarize a packet, explain why a claim is unresolved, compare packets, find contradictory documentation, draft a pre-registration (`proposed`), and suggest the next inert experiment. Answers must cite `assessment.json` or `records/`.
- They may not create or edit measurements, relabel synthetic data, alter raw evidence, fill missing records, register a pre-registration, accept a session, record a human review, or touch any arming, ignition, or launch gate.
- `query` answers the common questions (unresolved claims, model-only claims, conflicting requirements, missing measurements, items needing judgement, proposed experiments, file dependencies, and what the repository refuses to claim) directly from the record; nothing is generated prose.

AI may interpret the record. It may not rewrite reality.

## Exit codes and input contract

| Exit code | Meaning |
|---|---|
| `0` | Completed; an audit may still contain warnings |
| `1` | `check` found findings or stale documents; `audit` found data-quality errors (report still written); `reproduce` found a difference; `drift` found changed files |
| `2` | Invalid input, failed integrity verification, a record that promotes beyond its evidence, or an existing output directory |

Record errors produce no output: duplicate IDs or JSON keys, unknown references, dependency cycles, path traversal, symlinks, non-finite JSON numbers, synthetic rows in a non-synthetic artifact, physical classes without an accepted session, and gates or statuses beyond the evidence. Inputs are limited to 64 MiB per file and 250,000 CSV rows; execution records may not contain a DTD or entities. The verifier rejects extra unlisted files; Python bytecode caches are ignored.

## CI

The `Portable evidence review` job runs with no installed packages: it builds and verifies a packet, runs `python -m evidence check`, checks review figures, and exercises the synthetic demo. The `Python checks` job runs the tests with a JUnit record, reproduces every model output, and builds a packet with both run records attached. Both packets are retained as artifacts for 30 days. CI establishes that code compiles, tests pass, models reproduce, and records are consistent. It cannot establish that a mechanism works, a model is valid, timing is met, or anything is safe to fly.
