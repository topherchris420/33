# Responsible Disclosure and Safety Reports

Project 33 includes embedded firmware, a UDP dashboard command path, and safety-sensitive actuator behavior. Please report issues in a way that improves review without publishing instructions that could bypass command gates or encourage unsafe live-propulsion activity.

## What to Report Privately

Use GitHub private vulnerability reporting or contact the maintainer privately before opening a public issue for:

- A way to bypass arming, launch, ignition, actuator, or interlock gates.
- A dashboard or firmware command path that can trigger unsafe behavior.
- Credentials, secrets, or network details that should not be public.
- A defect that could make the system fail open instead of fail closed.

If private reporting is not available, open a minimal public issue that says a private safety/security report is needed. Do not include reproduction steps that would enable unsafe behavior.

## What Can Be Public

Public issues are appropriate for documentation mistakes, build failures, simulation/CAD review gaps, and inert bench evidence as long as they do not include unsafe live-propulsion instructions.

## Project Boundary

This repository is for inert bench validation, simulation, and supervised educational testing. It does not authorize live propulsion or flight activity.
