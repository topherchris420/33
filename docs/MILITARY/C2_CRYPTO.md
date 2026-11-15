# Combat Command-and-Control Security — IMPLEMENTATION (compile-verified)

**Phase 5 · Firmware: IMPLEMENTATION (compile-verified, not bench-tested).
Design and threat model below.** Phase 6.1 validates the chain on the bench.

## Scope override

`ENABLE_DASHBOARD_LAUNCH = true` (MIL-DEV-004): the dashboard remote-fire
path is the wartime norm, not the inert-bench exception. The original
default-off interlock is replaced by a STRONGER discipline, not a weaker one.

## Threat model

Adversary on the WiFi link (launcher AP): can capture, replay, inject, or jam
UDP packets. Cannot physically access the launcher or rocket (the UART link
between them is trusted by physical access).

## Command authentication (block forgery and replay)

- Weapons and configuration commands travel as
  `AUTH,<seq>,<operator>,<payload>,<hmac_hex>`.
- **HMAC-SHA256** over `seq,operator,payload` with the operator's key
  (0 = command key, 1/2 = operator keys), constant-time compare.
- **Monotonic sequence numbers with a 64-packet sliding replay window** —
  a captured `launch` cannot be re-sent (`seq <= lastSeq` inside the window
  is rejected).
- Plain `launch` remains accepted on the inert-bench path (READY-only);
  wartime procedure (operator card) always uses the authenticated form.

## Two-key OVERRIDE (positive weapons control)

A remote launch in READY additionally requires **either** a physical 1-second
fire-button hold within the last 5 seconds **or** a valid two-key OVERRIDE:

- `OVERRIDE,enabler,<nonce>,<hmacA>,<hmacB>` — the enabler must be signed
  by **BOTH operator keys** (two digital arms; a physical arm key plus one
  digital key satisfies the same intent on the bench).
- Valid for 60 seconds; each use is logged and telemetered.
- No single stolen key, single operator error, or single packet can fire the
  round. The SAFE→ARMING→READY→IGNITING interlock spine (G-01..G-07)
  remains the master logic; OVERRIDE adds authorization, never removes gates.

## Telemetry downlink (confidentiality + integrity)

- Launcher→dashboard packets are **AES-128-CCM** authenticated-encrypted
  (`ENC,<iv>,<ct>`; mbedtls on the launcher, `cryptography` on the dashboard).
- Crypto failure degrades to plain telemetry — **never silence**: the
  downlink fails open for visibility, the command path fails closed.
- Real-time content: rocket NAV (position/velocity/attitude), target track,
  fuze state, system health, plus the RAM ring-buffer post-strike dump
  (`dumplog` → `LOG` rows, unchanged).

## Jam resistance (option)

The design tolerates jamming by design rather than exotic waveforms: the
command path is a single small authenticated packet (retransmissible), the
telemetry stream is lossy-tolerant (ring buffer survives link loss), and the
physical interlock spine works with zero RF. An FHSS or spread-spectrum
radio upgrade is a documented option if the threat requires it; nothing in
the command logic depends on the bare WiFi PHY.

## Key management

Keys are provisioned constants in `Firmware/Launcher/src/crypto.cpp` and
mirrored in `Firmware/dashboard.py` — **bench defaults only, change before
fielding**. Key rotation is a manual reflash (documented procedure);
over-the-air rekeying is deliberately out of scope for this program's budget.

## Grep-able evidence

- `Firmware/Launcher/src/crypto.h/.cpp` — HMAC, AES-CCM, replay window,
  two-key OVERRIDE.
- `Firmware/Launcher/src/main.cpp` — AUTH unwrap, OVERRIDE handling,
  ENABLE_DASHBOARD_LAUNCH=true, ENABLE_TELEMETRY_CRYPTO=true, manual-fire
  window.
- `Firmware/dashboard.py` — `sign_command`, `decrypt_enc_packet`,
  fire-control panel (target/mode/fuze).
- Safety gates G-15..G-19 in `evidence/safety_gates.json`.
