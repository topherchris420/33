# Militarization Deviation Register

Every override of the repository's original inert bench-validation scope, and of
any standing rule changed during weaponization. Nothing here is hidden; each
entry names the rule overridden, the authority, and the consequence. Register
format follows the spirit of the inert-scope discrepancy register
([docs/DISCREPANCIES.md](../DISCREPANCIES.md)): resolved rules stay visible.

**Authority for all entries:** program sponsor direction of 2026-11-14,
converting Project 33 from a folding-fin rocket testbed into a deployable guided
munition. Chief weapons engineer: the committing author. Nothing in this
register authorizes live fire by itself; that authority is the phased live-fire
program in [LIVE_FIRE_PROGRAM.md](LIVE_FIRE_PROGRAM.md), executed under the
program sponsor's written order.

| ID | Rule overridden | Where the rule lived | Change | Phase | Status |
|---|---|---|---|---|---|
| MIL-DEV-001 | Repository remains an inert bench-validation prototype; tactical/weaponized framing not adopted | [docs/PAPER_ALIGNMENT.md](../PAPER_ALIGNMENT.md) integration boundary | Scope formally widened: Project 33 is now a guided-munition program. The inert bench record is preserved unchanged as the audit trail. | All | ACTIVE |
| MIL-DEV-002 | No live-propulsion or live-fire activity authorized by the repository | [docs/SAFETY.md](../SAFETY.md) | Live fire planned as a separately gated program ([LIVE_FIRE_PROGRAM.md](LIVE_FIRE_PROGRAM.md)) with its own pass/fail gates and log. Energetic work remains excluded from automated tests. | 6 | ACTIVE |
| MIL-DEV-003 | No targeting, live-fire, or autonomous-guidance behavior may be added | [docs/PAPER_ALIGNMENT.md](../PAPER_ALIGNMENT.md) | Terminal guidance toward a designated target point added (Phase 3). Autonomous engagement exists only behind an explicit arm-mode toggle; man-in-the-loop is the default. | 3 | ACTIVE |
| MIL-DEV-004 | Dashboard launch must be disabled by default | [docs/SAFETY.md](../SAFETY.md) G-04; `ENABLE_DASHBOARD_LAUNCH` | Set true in launcher firmware as the wartime remote-fire path (Phase 5), with command authentication, sequence numbers, and two-key OVERRIDE discipline replacing the default-off interlock. G-05 (READY-only), G-06 (source check), and the physical interlock spine remain. | 5 | ACTIVE |
| MIL-DEV-005 | Automated tools may not enable dashboard launch or change gates | [docs/SAFETY.md](../SAFETY.md) | The two-key OVERRIDE mode (two physical or two digital arms) is the replacement positive-weapons-control discipline; documented in [C2_CRYPTO.md](C2_CRYPTO.md) and [OPERATOR_CARD.md](OPERATOR_CARD.md). | 5 | ACTIVE |
| MIL-DEV-006 | Ignition servo is the sole ignition path | [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | Electric initiator added as the primary ignition path; ignition servo retained as backup (Phase 4). | 4 | ACTIVE |
| MIL-DEV-007 | PLA+/PETG airframe; 7075-T6 parts modeled only | [docs/CAD_ASSEMBLIES.md](../CAD_ASSEMBLIES.md); [materials/parts.yaml](../../materials/parts.yaml) | Composite (G-10/CFRP) load-path structure per the C8 laminate spec; 7075-T6 retained for load-path metallics (Phase 4). | 4 | ACTIVE |
| MIL-DEV-008 | Hobby motor (AeroTech G64W) is the propulsion baseline | [Simulation/Folding Stabilized Rocket.ork](../../Simulation/Folding%20Stabilized%20Rocket.ork) | Military-class solid motor sized for the 1–3 km tactical envelope (Phase 4); G64W retained as the Phase 6 inert-flight motor. | 4 | ACTIVE |
| MIL-DEV-009 | SG90-class plastic-gear servos for canards | [materials/bom.csv](../../materials/bom.csv) | Metal-gear digital servos sized from live aerodynamic loads (Phase 4). | 4 | ACTIVE |
| MIL-DEV-010 | Rocket deploy trigger requires >15 g launch acceleration (tube-launch assumption) | `Firmware/Rocket/src/main.cpp` | Threshold re-derived for rail launch at Phase 1 (the G64W cannot produce 15 g on this mass); sustained-acceleration threshold with time qualification substituted. See [PHASE1_GATES.md](PHASE1_GATES.md). | 1 | ACTIVE |
| MIL-DEV-011 | Rocket state machine has no path back from ARMED (aborted rocket stays armed) | Discrepancy D-025 | DISARM command added so an aborted round can be safed without restart (wartime misfire/abort drill requires it). | 5 | ACTIVE |

## Rules NOT overridden (still in force)

- Every claim stays labeled MODELED / MEASURED / FIELDLED; simulation is never
  presented as fielded performance.
- No AI feature, script, or CI job may send ARM/IGNITE/FIRE autonomously; the
  autonomous engagement mode is a firmware mode commanded by an operator behind
  an explicit arm toggle, not an automated tool.
- The SAFE→ARMING→READY→IGNITING interlock spine remains the master safety
  logic; OVERRIDE adds authorization, never removes gates.
- Evidence discipline: changed model inputs get an independent source or stay
  flagged (the D-009 rule now applies to militarized inputs too).
