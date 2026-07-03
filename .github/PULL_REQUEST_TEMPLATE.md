## Description

Please include a summary of the change and which issue is fixed (if applicable).

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Other: [describe]

## Testing

Please describe the testing you performed:

- [ ] Python tests pass: `python -m pytest tests Firmware/tests -q`
- [ ] Protocol check passes: `python tools/generate_protocol.py --check`
- [ ] Firmware builds: `pio run -d Firmware/Rocket && pio run -d Firmware/Launcher`
- [ ] Manual testing on hardware (if applicable)

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Additional context

Add any other context about the pull request here.