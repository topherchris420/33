# Bill of Materials

A planning BOM for the low-cost prototype. Every price below is an **estimate** from approximate small-quantity online prices; none is a purchase record. The table is generated from `materials/bom.csv`, so a changed line changes every cost figure in the documentation at once.

<!-- evidence:bom-table -->
| Item | Qty | Unit | Unit price | Price basis | Purchased price | Source date | Reused | Notes |
|---|---|---|---|---|---|---|---|---|
| ESP32 DevKit V1 | 2 | each | $6 | estimate | not recorded | not recorded | unknown | Rocket flight computer and launcher |
| MPU6050 IMU module | 1 | each | $4 | estimate | not recorded | not recorded | unknown | Rocket roll sensing |
| SG90-class micro servo | 5 | each | $3 | estimate | not recorded | not recorded | unknown | Four canards plus ignition servo; firmware drives six servos in total (D-021) |
| QMC5883L compass | 1 | each | $4 | estimate | not recorded | not recorded | unknown | Launcher heading estimate |
| BMP180 barometer | 1 | each | $3 | estimate | not recorded | not recorded | unknown | Launcher altitude/environment estimate |
| GPS receiver module | 1 | each | $10 | estimate | not recorded | not recorded | unknown | Launcher location/status |
| Switches, button, LED, buzzer | 1 | set | $5 | estimate | not recorded | not recorded | unknown | Physical launch interlock and indicators |
| Battery/regulator/wiring | 1 | set | $12 | estimate | not recorded | not recorded | unknown | Depends on available lab stock |
| FDM filament | 1 | spool share | $8 | estimate | not recorded | not recorded | unknown | Airframe/launcher printed parts |
| Fasteners, inserts, adhesives | 1 | set | $8 | estimate | not recorded | not recorded | unknown | Mechanical assembly |

**Subtotal of estimates:** $81 across 10 lines. 10 lines are estimates; 0 purchased prices are recorded. Shipping, spares, and tax are excluded. Source: `materials/bom.csv`.
<!-- /evidence:bom-table -->

## Price basis

| Field | Meaning |
|-------|---------|
| `price_basis` | `estimate`, `purchased`, `reused`, or `unknown` |
| `purchased_price_usd` | Blank means **not recorded**, not free |
| `source_date` | Blank means **not recorded**; estimates age |
| `reused` | `yes`, `no`, or `unknown`; reused parts have no purchase cost but are not free to replace |

Shipping, spares, tax, and tools are excluded. Known mismatch: the firmware drives six servos (five on the rocket, one on the launcher) and the folding-rocket CAD references an MG996R, while the BOM lists five SG90-class servos (D-021). Reconcile against an as-built inventory before citing a cost.

## Cost controls

- Use COTS hobby electronics for the proof of concept.
- Keep the launcher and rocket on ESP32 DevKit boards instead of custom PCBs.
- Use FDM prints for early structure and reserve machined/composite parts for later validation.
- Treat sensors as replaceable modules so failed bench tests do not destroy the whole system.

## Upgrade paths

| Upgrade | Why it matters | Trade-off |
|---------|----------------|-----------|
| Higher-torque servos | More control authority under aerodynamic load | Higher current draw and mass |
| Dedicated power regulation | Reduces brownout risk during servo motion | More wiring and cost |
| Better IMU | Lower drift and better vibration tolerance | More expensive and new driver work |
| Logging storage on rocket | Captures data if RF link drops | Adds mass and failure modes |
| Custom PCB | Cleaner wiring and repeatability | Higher design and fabrication effort |
