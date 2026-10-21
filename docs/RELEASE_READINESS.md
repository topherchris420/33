# Release decision: HOLD

This checkout can produce a review distribution. It cannot establish a production software-hardware release: the evidence record has no accepted physical measurements, procurement is estimated, and engineering contradictions remain open. The release audit does not change models, predictions, measurement registries, reviews, or discrepancy status to manufacture passing results.

The [engineering review](ENGINEERING_REVIEW.md) defines the next decisions and a bounded stationary-demonstrator milestone.

## Engineering dispositions

| Request | Observed evidence | Required next evidence |
|---|---|---|
| R-C1-CLOSURE: perfect physical closure | Ground/input lengths 25/15 mm allow a B-D separation of at most 40 mm at any angle. Coupler/output lengths 60/15 mm require at least 45 mm. The existing circle-intersection formula correctly rejects every baseline pose. CAD is illustrative and uses a different coupler (D-005). | Approve topology, pin-centre dimensions, assembly branch, tolerances, and drawing revision. Regenerate model and CAD together; independently measure assembly and locking. A mathematical closure alone does not prove physical fit. |
| R-C6-MARGIN: increase spring constant | The current heuristic reports 184.8838 required and 220 supplied, giving 18.9936% rather than 20%. The supplied value is a paper assumption. The routine adds inertial and aerodynamic torques and labels the result a spring rate without an explicit spring deflection relation. | Review dimensional consistency and torque-versus-angle assumptions; obtain a specimen/datasheet and approved load case. Preserve the registered 220 prediction; register a replacement if the spring changes. Raising a constant is not spring characterization. |
| R-C8-MODULUS: change structural density | The laminate model reports Ex = 56.68 GPa versus a 69 GPa requirement. Density is not an input to its constitutive stiffness calculation. Section thickness changes bending stiffness, not material modulus. | Traceable lamina properties, approved layup and both section geometries; distinguish Ex from EI and mass. Measure coupons/component stiffness as appropriate. |
| R-C5-WINDOW: match OpenRocket | Reference and cross-check disagree (about 1.55-1.57 versus 0.74-0.76 calibers). Motor, nose shape, mass handling, and formulation differ. The saved OpenRocket cache also falls outside the target window; its generating geometry revision is unknown. | Versioned component CP/CG exports with generating model hash, motor data, deployment configuration, coordinate origin, and flight condition. Review the formulations before defining comparison tolerances. Do not tune inputs or copy a target result. |

Models and CAD are retained pending those inputs. These are engineering design decisions; the automated audit records the remaining work.

`Simulation/openrocket_reference.py` extracts the actual cached trajectory from the committed `.ork` archive without fitting or changing either model. The file identifies its creator as OpenRocket 24.12 and its simulation status as `loaded`. In the single-motor 0-2.44 s burn window it contains 132 samples: 111 finite CP/margin values and 21 missing values. Finite CP spans 0.394-0.419 m, CG spans 0.333-0.343 m, and static margin spans 0.692-1.120 calibers. The target 1.5-2.0 window is not met by those cached finite values. Missing values stay null. The current archive hash identifies the file, not the geometry revision that generated its cache.

The extractor labels SI coordinates according to the [OpenRocket internal-unit convention](https://openrocket.readthedocs.io/en/latest/dev_guide/codebase_walkthrough.html). Its `openrocket-cache.json` output retains samples, a source SHA-256, saved configuration ID, separate trajectory/burn summaries, and limitations. No OpenRocket simulation is rerun by extraction, and this output does not replace the Observatory's analytical model artifacts.

## Procurement and physical evidence

D-021 includes five SG90-class servos in the BOM versus six firmware-controlled servos and an MG996R reference in CAD. A receipt alone cannot reconcile the as-built inventory. All ten prices remain estimates; $81 is not an established acquisition cost. The [purchase ledger](../evidence/materials/invoices.json) is empty and its [format](../evidence/materials/README.md) is documented.

| Experiment | Current registration | Why generated values cannot complete it |
|---|---|---|
| P-001 | Proposed 50 ms output delay; independent instrument; at least 1,000 trials | T packets carry a launcher relay clock and lack a physical deployment-complete channel. A 0-45 ms trace answers a different question. |
| P-002 | Proposed static torque-angle characterization | Requires a specimen, calibrated torque instrument, uncertainty and a tolerance registered before testing. |
| P-003 | Proposed exploratory 600 s stationary drift characterization | Has no pass/fail prediction. Ten invented seconds do not establish gyro drift. |
| P-006 | Absent | No registered laser sweep, line-of-sight sensor channel, or tracking-error measurement exists in the protocol. Define and review an experiment before claiming results. |

The synthetic generator creates a ten-second dashboard-format software fixture with in-band `synthetic` origin. Its passport stays audited and cannot be accepted as bench evidence. A separate mock planning-cost file is rejected as a purchase ledger. Neither is injected into the Observatory.

## Rebuild the review distribution

From the source checkout, using the installed Python environment:

```text
python tools/finalize_release.py --output dist
```

The script runs record/protocol/document/figure checks, cached OpenRocket extraction, the Python suite, model reproduction, and both PlatformIO builds. It copies binaries only from successful builds; includes logs, source, a verified review packet, and file hashes; and writes `release-review.json`. It never uploads firmware, commands hardware, signs a review, or modifies evidence records. JUnit case totals count every parameterized execution; requirement lookup still requires every parameter to pass.

Each named check must appear exactly once with a successful exit code. The audit requires a nonempty test run record and complete, current model-reproduction coverage. Skipped or failed tests remain blockers. Each firmware artifact set is published atomically only when all expected files are present and nonempty.

The [bench configuration workflow](BENCH_CONFIGURATION.md) adds configuration-bound observation metadata. Supply `--bench-plan` and `--bench-observations` to include its verified packet; missing or incomplete bench metadata adds a blocker. Complete metadata never substitutes for accepted physical measurements.

Exit 1 means the review distribution was created with unresolved release blockers. Exit 2 means packaging failed. `--skip-firmware` supports an offline review but records missing firmware checks as blockers. Existing output directories are never overwritten. The launcher needs its local WiFi configuration before building; see the [user guide](USER_GUIDE.md).

`python -m evidence check` returning 0 establishes record consistency only. Read requirement outcomes, open discrepancies, test skips, reproduction results, and measurement provenance separately. Package hashes identify bytes; independent human assessment establishes whether evidence supports a claim. No generated percentage or signature authorizes field use.
