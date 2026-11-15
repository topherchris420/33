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
