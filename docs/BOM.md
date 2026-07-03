# Bill of Materials

This is a planning BOM for the low-cost prototype. Prices are approximate small-quantity online prices and should be re-checked before purchase.

| Item | Qty | Typical Unit Cost | Est. Cost | Notes |
|------|-----|-------------------|-----------|-------|
| ESP32 DevKit V1 | 2 | $6 | $12 | Rocket flight computer and launcher |
| MPU6050 IMU module | 1 | $4 | $4 | Rocket roll sensing |
| SG90-class micro servo | 5 | $3 | $15 | Four canards plus ignition/interlock servo |
| QMC5883L compass | 1 | $4 | $4 | Launcher heading estimate |
| BMP180 barometer | 1 | $3 | $3 | Launcher altitude/environment estimate |
| GPS receiver module | 1 | $10 | $10 | Launcher location/status |
| Switches, button, LED, buzzer | 1 set | $5 | $5 | Physical launch interlock and indicators |
| Battery/regulator/wiring | 1 set | $12 | $12 | Depends on available lab stock |
| FDM filament | 1 spool share | $8 | $8 | Airframe/launcher printed parts |
| Fasteners, inserts, adhesives | 1 set | $8 | $8 | Mechanical assembly |

**Estimated prototype subtotal:** about **$81** before shipping and spares.

## Cost Controls

- Use COTS hobby electronics for the proof of concept.
- Keep the launcher and rocket on ESP32 DevKit boards instead of custom PCBs.
- Use FDM prints for early structure and reserve machined/composite parts for later validation.
- Treat sensors as replaceable modules so failed bench tests do not destroy the whole system.

## Upgrade Paths

| Upgrade | Why it matters | Trade-off |
|---------|----------------|-----------|
| Higher-torque servos | More control authority under aerodynamic load | Higher current draw and mass |
| Dedicated power regulation | Reduces brownout risk during servo motion | More wiring and cost |
| Better IMU | Lower drift and better vibration tolerance | More expensive and new driver work |
| Logging storage on rocket | Captures data if RF link drops | Adds mass and failure modes |
| Custom PCB | Cleaner wiring and repeatability | Higher design and fabrication effort |
