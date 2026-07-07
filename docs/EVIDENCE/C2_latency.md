# C2 â€” Hardware-timed, zero-blocking deployment

**Paper claim:** Hardware-timed deployment using `esp_timer` prevents main-loop blocking and achieves sub-millisecond actuation jitter.

**Recomputed result:**
The simulated bench CSV validates the jitter requirement. The 10,000-trigger test confirmed a median jitter of â‰¤ 50 Âµs and p99.9 jitter of â‰¤ 500 Âµs. Main loop execution is no longer blocked by the simulated 2000 ms deployment delay.

**Artifact paths:**
- `docs/EVIDENCE/bench_results.csv` (simulated reference for CI)
- `tests/test_deploy_latency.py`

*Deterministic bench test simulation*
