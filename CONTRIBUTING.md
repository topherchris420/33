# Contributing to Project 33

Thank you for your interest in contributing! This project demonstrates aerospace engineering with low-cost desktop tools, and we welcome contributions that align with this mission.

## Getting Started

### Prerequisites

- **PlatformIO** — for building and uploading ESP32 firmware
- **Python 3.11+** — for dashboard and tests
- **Git** — for version control

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

   pip install -r Firmware/requirements.txt
   pip install pytest
   ```

3. **Set up PlatformIO** (if building firmware)
   ```bash
   pip install platformio
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
| `docs/` | Architecture, wiring, protocol, safety docs |
| `tests/` | Python regression tests |
| `tools/` | Protocol generation utilities |

## Code Style

- **Python**: Follow PEP 8. Use meaningful variable names.
- **C++**: Use consistent bracing, 4-space indentation.
- **Documentation**: Use Markdown. Keep docs in sync with code changes.

## Pull Request Guidelines

1. **Branch strategy**: Create a feature branch from `main`
2. **Commit messages**: Use clear, descriptive commit messages
3. **PR description**: Include:
   - What changed
   - Why it matters
   - Testing performed
4. **Before submitting**:
   - Run `python -m pytest tests Firmware/tests -q`
   - Verify PlatformIO builds pass (`pio run -d Firmware/Rocket && pio run -d Firmware/Launcher`)
   - Ensure protocol check passes (`python tools/generate_protocol.py --check`)

## Safety Notice

This project involves embedded systems and (eventually) rocketry. When contributing:
- Test thoroughly on bench before any hardware deployment
- Do not modify safety-critical code without clear justification
- Document any changes to safety gates or interlock behavior

## Questions?

- Open an issue for bugs or feature requests
- Check the docs in `docs/` for detailed architecture and protocol info
- Review existing issues before creating new ones

We appreciate your contributions!