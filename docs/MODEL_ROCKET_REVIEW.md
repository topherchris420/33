# Model-rocket altimeter and recovery review

Project 33 now includes a standalone pressure-logger firmware image, an offline
height/rate estimator and recovery-event model, and an interactive laboratory
timeline. These are implemented software functions. The release event is a
simulated marker in a report; it does not operate a parachute mechanism.

The supplied aircraft supplement does not specify a model-rocket altimeter,
parachute, controller, wiring or deployment algorithm. The choices here are
original Project 33 bench specifications. They use the manual's broad themes of
source validity, clear mode indication and failure review, without copying
aircraft procedures or presenting them as rocket requirements.

## Selected bench hardware

Use a separate ESP32 DevKit and BMP180 module with 3.3 V compatible I2C pull-ups.
The BMP180 family and ESP32 already occur in the project; an additional specimen
is proposed for this demonstrator. The existing launcher's barometer stays a
ground sensor. No installed hardware is presumed or verified.

| Bench connection | ESP32 assignment |
|---|---|
| BMP180 SDA | GPIO 21 |
| BMP180 SCL | GPIO 22 |
| Compatible module supply / ground | 3.3 V / GND |
| BMP180 I2C address / chip ID | 0x77 / 0x55 |
| Observation transport | USB serial, 115200 baud |
| Actuator connections | None |

Build without connecting a board:

```bash
pio run -d Firmware/Rocket -e altimeter_bench
```

The build selects only `src/altimeter_bench.cpp`, excluding the normal flight and
deployment code. It checks initialization, the chip-ID register and pressure
validity, then emits a `P33BARO` record every 200 ms. Initialization failures are
retried every five seconds. Boot nonce, sequence, device uptime and reported ELF
digest accompany every sample. Invalid pressure is `nan`, never zero. Driver
success is not calibration, fault coverage or proof of a functioning pressure port.
There is no actuator, command receiver or radio interface in this image.

No board was flashed or observed for this implementation. Opening USB can reset
an ESP32. A named operator chooses and performs any stationary inert observation
under the existing [bench rules](SAFETY.md); this document does not establish
flight suitability.

## Exercise the complete software path

```bash
python Firmware/altimeter_review.py demo --output build/altimeter-demo-log.json
python Firmware/altimeter_review.py review build/altimeter-demo-log.json --output build/altimeter-demo-review.json
python tools/build_altimeter_example.py --check
```

Open [Instrumentation Lab](../lab/instruments.html#altimeter-title) and select
**Load synthetic flight example**, or load the generated review JSON. Scrub the
timeline to inspect pressure, relative height, vertical rate, validity and phase.
The committed example is explicitly synthetic, including its invented observer
annotations. It demonstrates 120 m of modeled rise followed by descent, without
representing a real rocket or a prediction of Project 33 performance.

The existing USB tool can preserve the new firmware's raw output. Its normal
monitor report counts `P33BARO` as unrelated text; the separate importer below
understands those frames. An operator may run the following capture; automation
in this task has not opened any port:

```bash
python Firmware/bench_monitor.py capture --port COM7 --seconds 60 --output build/altimeter-capture
python Firmware/altimeter_review.py import-usb build/altimeter-capture --pressure-pa 101325 --temperature-k 288.08 --reference-note "Replace these example numbers with the declared stationary reference" --output build/altimeter-import.json
python Firmware/altimeter_review.py review build/altimeter-import.json --output build/altimeter-import-review.json
```

All output paths must be new. Imported logs remain `stationary_bench`, retain
declared synthetic or undeclared origin, and carry the verified raw-file digest
and reported ELF digest. The importer checks the raw capture digest, frame
shape, firmware-identity conflicts, sequence/clock progression, and uptime wrap.
It requires `--boot HEX16` if multiple boots are present. Missing sequence numbers
insert an invalid boundary. A matching digest establishes file identity, not
authentic hardware origin. Preserve the capture; write derived outputs outside it.

## Input and model

`project33.altimeter_log/1` declares sensor identity and mount (`rocket`,
`launcher` or `stationary_bench`), a stationary reference pressure in Pa and air
temperature in K, and ordered samples. Each sample includes `time_s`, `valid`,
`pressure_pa` and an in-band `origin` of `synthetic` or `undeclared`. Invalid
pressure must be null. See the [complete example](../lab/data/altimeter_example_log.json).
Existing dashboard `ENV` altitude and launcher BMP180 observations cannot be
relabelled as onboard rocket measurements. This tool does not import them as such.

The local reference model estimates
`h = (T_ref / 0.00649) * (1 - (p / p_ref) ** (1 / 5.256))`.
This is a relative linear-lapse pressure model based on the troposphere form
described by [NASA Glenn](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/earth-atmosphere-equation-metric/).
Applying that form to a declared local reference is this project's modeling
choice. It is not geometric altitude, height above terrain, or an independent
navigation solution. Weather, port dynamics, temperature assumptions, noise and
motion can all bias it. The software domain of -1000 to 11000 relative meters is
a model guard, not a vehicle operating envelope.

The [review settings](../protocol/altimeter_review.json) use a trailing 0.8 s
least-squares slope with at least three samples. A gap longer than 1 s or an
invalid/model-out-of-range sample breaks the segment and clears phase history.
No slope, ascent-to-descent transition or release marker bridges that boundary.
Warmup samples show height with no vertical-rate estimate.

For a declared rocket source, rising at least 2 m/s above 5 m for 0.6 s emits an
`ASCENT_REVIEW` marker. A subsequent drop of at least 2 m from the segment's sampled
peak and a falling rate of at least 2 m/s for 0.6 s emits one
`SIMULATED_RELEASE_MARKER` in that segment. These are demonstration review
thresholds, not qualified deployment settings. The sampled peak and detection
time are separate fields; neither establishes the actual apogee. Ground and
stationary bench sources never emit model-rocket markers.

Optional `parachute_observed` and `ground_contact_observed` annotations require
an observer, time and note. They remain declarations. Pressure trends cannot
prove parachute opening, ground contact, safe descent or recovery success. No
automatic landing or successful-recovery verdict is produced. The NAR describes
model-rocket recovery systems such as parachutes or streamers in its
[Model Rocket Safety Code](https://www.nar.org/ModelRocketSafetyCode); this data
review is not a replacement for such a system.

## Evidence and remaining implementation

Reports include input, model and analyzer digests, declared origins and data-quality
counts. The browser validates their structure and displays the supplied report;
it does not recompute it or verify raw files. Re-run the Python review from the
preserved input for reproducibility. The synthetic example has a freshness check
in CI. No evidence measurements, human approvals or accepted sessions are added.

Physical parachute deployment, installed recovery hardware, independent backup,
actuator timing, power-loss behavior and flight performance remain unimplemented
and unmeasured. The existing rocket's fin deployment and ignition logic are
different mechanisms; this work does not change their gates or behavior.
