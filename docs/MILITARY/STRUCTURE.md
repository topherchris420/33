# Military Structure and Motor — MODELED

**Phase 4 · Evidence class: MODELED** (the C8 laminate calculation remains
analytical). No coupon, component, or motor has been tested.

## Airframe (MIL-DEV-007)

| Element | Phase 1–3 | Phase 4 | Basis |
|---|---|---|---|
| Body tubes | fiberglass 2.54 mm | **G-10/epoxy 2.0 mm** | C8 laminate spec; −0.13 kg |
| Load-path metallics | modeled only | **7075-T6**: 3 mm hinge pins, motor-mount rings, warhead case | MIL-DEV-007 |
| Fins | molded CFRP | unchanged (already Phase 1 spec) | — |
| Canard servos | SG90 (plastic gear) | **metal-gear digital, 30 kg·cm class** | sized below |
| Printed PLA+/PETG airframe parts | baseline | superseded (bench fixtures only) | storage-temp budget |

### Structural checks (closed-form, MODELED)

- **Laminate (C8, unchanged):** quasi-isotropic CFRP Ex = 56.7 GPa vs
  6061-T6 69 GPa — the material-modulus comparison still fails (D-015 stays
  open honestly); the militarized fin is a thickness-designed CFRP sandwich
  where the equal-mass section stiffness is what matters (R-C8-COMPONENT-
  STIFFNESS remains a human-review item).
- **Hinge pin, militarized load case:** 7075-T6, 3 mm pin, 12 mm gap, under
  the Phase 4 launch-shock design load (65.7 g = 3 × the MIL-33 initial
  acceleration): von Mises 88.0 MPa → **FOS = 5.71** (≥ 1.5 requirement)
  — `docs/EVIDENCE/C8_hinge_fos_military.json`.
- **Canard servo sizing:** at burnout dynamic pressure (≈425 m/s modeled,
  15° effective alpha) each canard sees ≈135.6 N → hinge torque 1.72 N·m
  (17.5 kg·cm). Specified 30 kg·cm metal-gear digital servos give ≈1.7×
  torque margin, and metal gears survive the vibration budget that stripped
  SG90s would not.

## Motor (MIL-DEV-008): MIL-33

Sized by bisection on the CEP model's drag physics for a 3.3 km ballistic
envelope (3 km + 10% margin), propellant Isp assumption 200 s:

| Property | Value (MODELED) |
|---|---|
| Total impulse | **1,235 N·s** |
| Burn time / avg thrust | 2.0 s / 617 N |
| Propellant / motor wet / dry | 0.63 / 1.24 / 0.61 kg |
| Round wet mass | 2.87 kg |
| Initial acceleration | 21.9 g |
| Ballistic envelope (best elevation) | 3.30 km |
| Thrust curve | `Simulation/MIL-33.eng` (RASP, PREDICTED plateau; import into OpenRocket) |
| Ignition | **electric initiator primary; ignition servo retained as backup** (MIL-DEV-006) |

The committed `.ork` carries the MIL-33 designation and envelope with the
Phase 4 composite-structure mass overrides; the thrust curve itself is the
committed `.eng` file. The AeroTech G64W remains the Phase 6 inert-flight
motor.

## Environmental budgets (MIL-STD-810-style, METHOD-derived targets)

| Budget | Design value | Check |
|---|---|---|
| Launch shock | **65.7 g** design load (3 × 21.9 g) | hinge FOS 5.71 ✓; canard servo hold-torque ✓ |
| Vibration | 20–2000 Hz random, method 514 style | canards must hold position under burnout q; metal-gear servos specified |
| Storage temperature | **−40 to +60 °C** | motor, spring, electronics rated over range; PLA+ superseded partly because it leaves this window |

These are budgets and closed-form checks, **not** test results. The
Phase 6.1 gate adds bench shock/vibration and thermal storage validation.

## What is still open

- D-015 (laminate modulus vs aluminium) stays open: the honest statement is
  that CFRP wins on equal-mass section stiffness, not material modulus, and
  the equal-mass calculation is a Phase 6 review item.
- The MIL-33 thrust curve is a predicted plateau; a static fire is the
  Phase 6.2 gate.
