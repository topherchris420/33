# Project 33 Militarization Evidence Tree

This tree holds the weaponized-program evidence: warhead and fuze claim
passports, CEP and lethality estimates, the militarization deviation register,
and the live-fire test log. It exists because the program sponsor formally
overrode the repository's inert bench-validation scope on 2026-11-14
(see [DEVIATIONS.md](DEVIATIONS.md)).

## Evidence labels used in this tree

Every quantitative claim in `docs/MILITARY/` carries exactly one label:

| Label | Meaning |
|---|---|
| **MODELED** | Output of a calculation or simulation committed to this repository. Only as good as its formulation and inputs. No hardware observed. |
| **MEASURED** | Physical measurement with a named instrument, method, and uncertainty, accepted by a named human. |
| **FIELDLED** | Performance demonstrated by a live round under the live-fire test program (see [LIVE_FIRE_LOG.md](LIVE_FIRE_LOG.md)). |

As of the Phase 1 militarization commit, everything in this tree is **MODELED**.
Nothing has been measured on militarized hardware, and no round has flown.

## Contents

| File | Contents |
|---|---|
| [DEVIATIONS.md](DEVIATIONS.md) | Militarization deviation register: every override of the original inert-scope rules, with what was overridden and why |
| [PHASE1_GATES.md](PHASE1_GATES.md) | Phase 1 gate report: linkage closure and over-center lock, static-margin resolution, deployment reliability |
| [WARHEADS.md](WARHEADS.md) | Warhead loadout claim passports (Phase 2) |
| [FUZE.md](FUZE.md) | Fuze and S&A design claim passport (Phase 2) |
| [TERMINAL_BALLISTICS.md](TERMINAL_BALLISTICS.md) | Lethality and penetration estimates with stated assumptions (Phase 2) |
| [GUIDANCE.md](GUIDANCE.md) | Terminal guidance design and CEP estimates (Phase 3) |
| [STRUCTURE.md](STRUCTURE.md) | Military airframe, motor, and environmental budgets (Phase 4) |
| [C2_CRYPTO.md](C2_CRYPTO.md) | Combat command-and-control security design (Phase 5) |
| [LIVE_FIRE_PROGRAM.md](LIVE_FIRE_PROGRAM.md) | Phased live-fire test program with pass/fail gates (Phase 6) |
| [LIVE_FIRE_LOG.md](LIVE_FIRE_LOG.md) | Live-fire test log (filled as phases execute) |
| [OPERATOR_CARD.md](OPERATOR_CARD.md) | One-page warfighter operator card (Phase 6) |

## Relationship to the inert evidence record

The original claim passports (C1–C8) remain in [docs/claims](../claims/README.md)
and continue to describe the bench-validation program with their own evidence
ladder. Where a militarization change invalidates an inert-scope rule, the
override is recorded in [DEVIATIONS.md](DEVIATIONS.md), never silently deleted.
The inert record is the audit trail that makes the militarized record credible.

## Technology provenance (Phase 6)

Four fire-control technologies were adopted from **TO 1F-117A-1A, OC-IP
Supplement to the Utility Flight Manual, USAF Series F-117A Aircraft
(3 Feb 1992)** — the program sponsor's reference copy (a 94 MB scan in the
sponsor's Downloads; **the scan itself is deliberately NOT committed**, per
this repository's own manual-scan rule, `tests/test_lab_data.py::
test_manual_scan_is_not_published`):

| Adopted technology | F-117 source concept | Project 33 implementation |
|---|---|---|
| **BIT** — preflight built-in test | FCS prestart BIT procedure (numbered tests, pass/fail per item) | `BIT` command: rocket replies `BIT,<mpu>,<gps>,<fuze>,<fins>,<mode>,<target>,<state>`; the dashboard renders it so the operator's pre-fire checklist is machine-checked, not trusted |
| **MARK** — one-button designation | MARK points (store current position as a destination) | `MARK` command: the launcher designates its own surveyed GPS position as the target and echoes `MARK,<lat>,<lon>,<alt>` back for verification |
| **Range readout + out-of-envelope warning** | HUD range readout; out-of-corridor warning symbol | Dashboard fire-control advisory: great-circle range and bearing from the launcher GPS fix to the target, red **OUT OF ENVELOPE — DO NOT FIRE** beyond the MIL-33 ballistic envelope (3.3 km) |
| **TTG/ETA** | HUD time-to-go / estimated time of arrival | Time-to-go from range and live ground speed (NAV packets in flight; modeled 200 m/s cruise on the ground) |

The display doctrine also matches the F-117's invalidity-flagging rule the
repository already follows: invalid data is flagged, never zero-filled.

