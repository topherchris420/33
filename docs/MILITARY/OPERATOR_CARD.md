# PROJECT 33 — WARFIGHTER OPERATOR CARD

**One page. Keep at the launcher.** Positive weapons control is YOUR job;
the machine only enforces what you check.

---

## PRE-FIRE CHECKLIST (2 minutes)

1. **SAFE** — launcher switch down, buzzer quiet, LED off.
2. **ROUND** — correct loadout (GP / HEAT / EFP); fuze delay set (0/5/10/20 ms);
   canards and fins free; motor installed (MIL-33 tactical / G64W training).
3. **KEYS** — launcher and dashboard keys are the FIELD set, not bench
   defaults (ask the armorer).
4. **LINK** — dashboard connected to launcher AP; `FUZE,SAFE` and rocket
   heartbeat visible; GPS fix on launcher.
5. **TARGET** — enter target lat/lon/alt on the fire-control panel → **SET
   TARGET** → confirm the rocket echoes it. Wrong target = wrong place.
6. **MODE** — `MITL` unless ordered otherwise. `AUTO` (fire-and-forget) only
   on explicit order — it is an arm-mode decision, not a convenience.

## ARM

7. Flip the arm switch → launcher runs its handshake (LEDs, tones) → **READY**
   when the rocket reports READY. Rocket is now ARMED; treat it so.
8. Fuze will arm itself only after real launch + canard deploy + burn time.
   `FUZE,SAFE` after abort is normal until restart.

## FIRE — two ways, both need READY

- **MANUAL (preferred):** hold the fire button 1 full second (buzzer).
- **REMOTE (dashboard DIGITAL LAUNCH):** needs EITHER a button hold within
  the last 5 s OR a two-key OVERRIDE. Two keys = two operators each signing
  `OVERRIDE,enabler` (or armorer key + one operator key). No single key,
  officer, or packet can fire this round.

## ABORT / MISFIRE DRILL

- **Switch off** → launcher safes and aborts (buzzer + `ABORT:` row logged).
- **The rocket stays armed up to 60 s** after an abort (deploy trigger live).
  Keep the rail clear; do not approach until the dashboard shows the rocket
  restarted to `IDLE` / `FUZE,SAFE`.
- **Misfire (no IGNITED within 5 s):** launcher aborts automatically. Wait
  60 s, switch to SAFE, then approach from the side per range rules.
- **Lost link:** physical interlocks still work; the round cannot fire on RF
  alone without the switch armed AND the fire discipline above.

## AFTER THE SHOT

- Watch `NAV` + `FUZE` telemetry; request **DUMP LOG** after impact — the RAM
  ring buffer survives the crash and is the shot's legal record.
- File the session folder to the live-fire log the same day.

---

**LABELS:** everything on this card is about hardware rules that are
compile-verified only; warhead effects and CEP numbers are MODELED until the
live-fire program says MEASURED or FIELDLED.
