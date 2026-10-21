# Configuration-bound bench observations

The offline bench workflow implements configuration identity, typed observation
metadata and an inspectable readiness report. It creates proposals and review
candidates. It does not operate hardware, choose new design dimensions, evaluate
performance limits, register measurements or accept sessions.

## What is now checked

| Concern | Implemented check |
|---|---|
| One identifiable configuration | Snapshot of the catalog, its current artifacts, record files, evidence implementation and firmware/capture inputs; added, missing or changed selected files produce findings. |
| Actual specimen identity | A hardware revision, specimen ID and description must be supplied. Captured identities must match the plan. |
| Installed software identity | Explicit binary SHA-256 digests per declared component; the capture must report the same identities. Source identity alone does not identify the flashed binary. |
| Meaning and units | Named quantity, canonical unit, observed phenomenon and source type must agree. Density cannot be labeled modulus; electrical transition timing cannot be labeled mechanical completion. |
| Command versus observation | Command requests, telemetry estimates and independent instrument observations have distinct types. Dashboard command/telemetry files cannot be used as independent instrument files. |
| Prior interpretation | Conditions, method, interpretation rule and a sourced comparison criterion are required. Characterization needs an explicit interpretation but has no pass/fail threshold. The referenced pre-registration must be human-registered and unchanged. |
| Instrument provenance | Independent readings require instrument identity, a hashed calibration document and declared calibration dates covering the capture. |
| Raw file integrity | Raw files must exist, be nonempty and match their supplied digests. Known synthetic CSV origin labels produce findings. |
| Traceability | Observations bind to the exact plan bytes. Retroactive plans, later registration dates, future capture times and differing specimen/software identities produce findings. |

These are checks of structure and declared provenance. A person still needs to
assess the meaning and authenticity of the inputs. A supplied scalar summary is
not independently recomputed from arbitrary instrument files; it cannot, by
itself, establish trial counts, timing jitter, reliability or completed motion.

## Create and freeze a plan

From the repository root:

```text
python -m evidence bench init --output build/bench-plan
```

The new directory contains `plan.json` and instructions. Defaults reference the
existing P-001, P-002 and P-003 proposals. Hardware identities, binary digests,
conditions and methods are left unknown. No performance values are invented.
The current proposals remain unregistered, so the initial report is blocked.

A responsible human must review and register the intended experiment through
the existing evidence process before collecting observations. Generate the
configuration snapshot after that record change. Complete the plan from the
selected specimen, installed binaries and reviewed method. Keep the same
finished plan bytes with the capture. Preserve earlier proposals; use a new
directory when creating a new configuration.

The source snapshot is an identity record, not an assertion that CAD, the BOM
and the analytical models describe compatible designs. Their existing
discrepancies remain open. The private `wifi_config.h` is excluded from source
snapshots; an installed binary digest is supplied independently.

## Create an empty observation record

After completing the plan and before the observation:

```text
python -m evidence bench template build/bench-plan/plan.json --output build/bench-observations
```

The generated `observations.json` binds to the plan digest. Its origin is
`unknown`; capture identities, values and uncertainties are null. This is an
empty form, not synthetic measurement data. Only information from the actual
reviewed session should fill these fields.

Each observation needs a quantity, unit, phenomenon, source type, value,
uncertainty, timebase and raw-file reference. An independent observation also
needs an `instrument` object with `id`, `calibrated_on`, `valid_until` and
`calibration_file`. Raw and calibration references use this shape:

```json
{"path": "relative/path/to/original-file", "sha256": "<actual SHA-256 of that file>"}
```

Paths are relative to the folder containing `observations.json`. Path traversal
and symlinks are rejected. Keep raw files unchanged. If a measurement is absent,
retain null. If a file is synthetic, declare the capture synthetic; it cannot
become a physical review candidate.

Canonical units are: `s`, `deg`, `deg/s`, `m`, `kg`, `kg/m^3`, `N*m`,
`N*m/rad`, `Pa` and `N*m^2` for the respective named quantities. The checker
does not silently convert units. Retain the original raw data and document any
conversion in the reviewed method.

## Build and inspect the review

```text
python -m evidence bench check build/bench-plan/plan.json --observations build/bench-observations/observations.json --output build/bench-readiness
python -m evidence verify build/bench-readiness
```

Open `build/bench-readiness/index.html`. The packet includes the plan,
observation metadata, referenced raw/calibration files, findings, a manifest
and an offline verifier. `readiness.json` reports one of:

- `blocked`: required metadata is missing, inconsistent or unsuitable.
- `plan_review_candidate`: metadata is complete, but no observations were supplied.
- `observation_review_candidate`: declared observation metadata is complete and
  its referenced files match. A human must still assess it.

Exit 0 means metadata checks passed. Exit 1 means findings are available in the
report. Exit 2 means invalid input or a file error prevented a complete report.
Every result retains `release_authorized: false`, `human_signoff: null` and
`measurement_acceptance: "NOT PERFORMED"`.

The existing [session passport and acceptance process](BENCH_SESSIONS.md) remains
separate. Review the configuration packet alongside the session passport.
This tool never inserts it into the measurement or session registries, and a
candidate packet does not satisfy any claim automatically.

## Include it in a distribution

```text
python tools/finalize_release.py --bench-plan build/bench-plan/plan.json --bench-observations build/bench-observations/observations.json --output build/review-distribution
```

The packet is copied into the distribution as `bench/` and independently checked.
A missing plan or incomplete observation packet adds a release blocker. All
existing discrepancy, requirement, procurement and physical-acceptance gates
remain in effect. A complete metadata packet does not override them.
