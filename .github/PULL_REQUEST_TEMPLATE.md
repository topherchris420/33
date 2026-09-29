## Purpose

Explain why this change is needed and what reviewer-facing claim it supports.

## Scope

- [ ] Firmware
- [ ] Dashboard / Python tools
- [ ] CAD / simulation assets
- [ ] Documentation
- [ ] CI / tests
- [ ] Safety boundary or command gating

## Safety Impact

- Does this alter arming, launch, ignition, servo motion, command validation, or interlock behavior?
- If yes, describe the changed gate, the failure mode considered, and the rollback path.
- If no, write `No safety-impacting behavior changed`.

## Evidence Added or Updated

List the source, test, CI, bench-session, image, CAD, or documentation artifacts that support this change.

## Evidence Record

- Claims whose review this change affects (`python -m evidence impact PATH`):
- Were those reviews re-snapshotted? By tooling (`snapshot`) or by a named human (`--reviewer`)?
- New or changed requirements, predictions, discrepancies, or pre-registrations:
- Evidence class of anything new (a model is not a measurement; synthetic is never physical):

## Verification

- [ ] Record check: `python -m evidence check`
- [ ] Protocol check: `python tools/generate_protocol.py --check`
- [ ] Python tests: `python -m pytest tests Firmware/tests -q`
- [ ] Rocket firmware build: `pio run -d Firmware/Rocket`
- [ ] Launcher firmware build: `pio run -d Firmware/Launcher`
- [ ] Manual inert bench test, if applicable
- [ ] Documentation links and images checked

## Not Tested

List known gaps honestly. Use `None` only when every relevant check above was performed.

## Reviewer Notes

Call out anything that deserves extra attention: assumptions, risk, hardware dependency, generated files, or evidence that should not be over-interpreted.
