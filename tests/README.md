# Sentinel Testing Suite

This directory contains the test suite for the Sentinel trading system.

## Structure

```
tests/
├── conftest.py          # Shared pytest fixtures
├── unit/                # Unit tests for individual components
│   ├── test_gates.py    # Gate system tests
│   ├── test_state.py    # State engine tests
│   └── test_websocket.py # WebSocket manager tests
├── integration/         # Integration tests (coming soon)
└── e2e/                 # End-to-end tests (coming soon)
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=core --cov=api --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_gates.py
```

### Run specific test class
```bash
pytest tests/unit/test_gates.py::TestFreshnessGate
```

### Run specific test
```bash
pytest tests/unit/test_gates.py::TestFreshnessGate::test_fresh_signal_passes
```

### Run tests by marker
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Test Coverage Goals

- **Unit Tests**: 80%+ coverage
- **Integration Tests**: Critical paths covered
- **E2E Tests**: Main user workflows

## Writing Tests

### Unit Tests
- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Focus on edge cases and error handling

### Integration Tests
- Test interaction between components
- Use real dependencies where possible
- Test configuration and state management

### E2E Tests
- Test complete user workflows
- Test signal processing end-to-end
- Test broker integrations (with testnet)

## Fixtures

Common fixtures are defined in `conftest.py`:
- `temp_data_dir`: Temporary directory for test data
- `mock_state`: Mock GlobalState instance
- `mock_signal`: Mock SignalPayload instance
- `mock_config`: Mock RuntimeConfig instance

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:
- Fast unit tests run on every commit
- Integration tests run on PR
- E2E tests run before deployment
