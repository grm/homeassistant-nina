---
name: run-tests
description: Run the test suite for the NINA integration
---

# Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_sensor.py -v

# Run with coverage
pytest tests/ --cov=custom_components.nina_astro --cov-report=term-missing

# Type checking
mypy custom_components/nina_astro/

# Linting
ruff check custom_components/nina_astro/
ruff format --check custom_components/nina_astro/
```
