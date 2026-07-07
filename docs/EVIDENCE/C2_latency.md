# C2 — Hardware-timed, zero-blocking deployment

**Paper claim:** Hardware-timed deployment using `esp_timer` prevents main-loop blocking and achieves sub-millisecond actuation jitter.

**Recomputed result:**
The C2 latency CSV is synthetic reference data generated for CI validation. The 21-row simulated bench CSV validates the jitter requirement with a median jitter of ≤ 50 µs and p99.9 jitter of ≤ 500 µs. Real bench captures require physical ESP32 hardware and are not yet available.

**Artifact paths:**
- `docs/EVIDENCE/C2_latency.csv` (synthetic reference for CI)
- `tests/test_deploy_latency.py`

*Synthetic bench simulation — awaiting real hardware capture*
