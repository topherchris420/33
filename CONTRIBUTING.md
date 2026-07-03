# Contributing to Project 33

Thank you for your interest in contributing. Project 33 is an evidence-first aerospace prototype: useful changes should make the system easier to build, review, test, or document without overstating what has been validated.

## Getting Started

### Prerequisites

- **PlatformIO** - for building and uploading ESP32 firmware
- **Python 3.11+** - for dashboard and tests
- **Git** - for version control

### Development Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/topherchris420/33.git
   cd 33
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate     # Windows

   pip install -r Firmware/requirements-test.txt
   ```

3. **Set up PlatformIO** (if building firmware)
   ```bash
   pip install -r Firmware/requirements-platformio.txt
   ```

## Running Tests

### Python Tests

```bash
python -m pytest tests Firmware/tests -q
```

### Protocol Generation Check

```bash
python tools/generate_protocol.py --check
```

### Firmware Build (without hardware)

```bash
pio run -d Firmware/Rocket
pio run -d Firmware/Launcher
```

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `Firmware/Rocket/` | PlatformIO project for rocket flight computer |
| `Firmware/Launcher/` | PlatformIO project for launcher ground station |
| `Firmware/dashboard.py` | Python telemetry dashboard |
| `docs/` | Status, architecture, wiring, protocol, evidence, and safety docs |
| `tests/` | Python regression tests |
| `tools/` | Protocol generation utilities |

## Contribution Standards

- Keep changes scoped and reviewable.
- Prefer evidence over assertion: link to source, tests, CI output, bench logs, photos, or explicit `not measured` notes.
- Update docs when behavior, wiring, protocol, safety gates, or evidence workflows change.
- Do not add dependencies without a clear reason and reviewer visibility.
- Do not imply flight, propulsion, or live-ignition validation unless that evidence exists and has been reviewed.

## Code Style

- **Python**: Follow PEP 8. Use meaningful variable names.
- **C++**: Use consistent bracing, 4-space indentation.
- **Documentation**: Use Markdown. Keep docs in sync with code changes.

## Pull Request Guidelines

1. **Branch strategy**: Create a feature branch from `main`.
2. **Commit messages**: Explain why the change was made, not only what changed.
3. **PR description**: Include:
   - What changed
   - Why it matters
   - Safety impact, especially for command gates or actuator behavior
   - Evidence added or updated
   - Testing performed
4. **Before submitting**:
   - Run `python -m pytest tests Firmware/tests -q`
   - Verify PlatformIO builds pass (`pio run -d Firmware/Rocket` and `pio run -d Firmware/Launcher`)
   - Ensure protocol check passes (`python tools/generate_protocol.py --check`)

## Safety Notice

This project involves embedded systems and rocketry-adjacent hardware. When contributing:

- Treat live propulsion or ignition work as outside the repository's current claim boundary.
- Test thoroughly on inert bench hardware before claiming hardware behavior.
- Do not modify safety-critical code without clear justification and rollback notes.
- Document any changes to safety gates, command validation, interlocks, or actuator behavior.
- Use [SECURITY.md](SECURITY.md) for private safety/security reports.

## Questions?

- Open an issue for bugs or feature requests.
- Check the docs in `docs/` for detailed architecture, protocol, status, and safety info.
- Review existing issues before creating new ones.
