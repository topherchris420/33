# C2 — Hardware-timed, zero-blocking deployment

**Paper claim:** Hardware-timed deployment using `esp_timer` prevents main-loop blocking and achieves sub-millisecond actuation jitter.

**Recomputed result:**
The C2 latency CSV contains 21 synthetic reference rows for software regression
checks. Its values do not validate a hardware jitter requirement or establish a
physical tail-latency bound. Real inert bench captures require physical hardware,
a documented timing instrument and method, and an uncertainty assessment; they
are not yet available.

**Artifact paths:**
- `docs/EVIDENCE/C2_latency.csv` (synthetic reference for CI)
- `tests/test_deploy_latency.py`

*Synthetic bench simulation — awaiting real hardware capture*
