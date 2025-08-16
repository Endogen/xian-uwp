# Xian UWP Test Suite

This directory contains comprehensive tests for the Xian Universal Wallet Protocol, organized by functionality and test type.

## 🧪 Test Structure

### Test Categories

| Test File | Category | Description | Test Count |
|-----------|----------|-------------|------------|
| `test_models.py` | Unit | Data models, enums, validation | ~15 |
| `test_server.py` | Unit | Server functionality, endpoints | ~20 |
| `test_client.py` | Unit | Client library functionality | ~15 |
| `test_cors.py` | Integration | CORS configuration and middleware | ~12 |
| `test_auth.py` | Integration | Authentication and permissions | ~18 |
| `test_e2e.py` | E2E | Complete wallet-DApp scenarios | ~8 |

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast unit tests (< 1s each)
- `@pytest.mark.integration` - Integration tests with real HTTP calls
- `@pytest.mark.e2e` - End-to-end scenarios with full server setup
- `@pytest.mark.cors` - CORS-specific functionality tests
- `@pytest.mark.slow` - Tests that take longer to run

## 🚀 Running Tests

### Install Test Dependencies

```bash
# Install all dependencies including test tools
poetry install --with test

# Or with pip (if not using Poetry)
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

**⚠️ Important**: You must install test dependencies first, otherwise you'll get coverage-related errors.

### Run All Tests

```bash
# Run complete test suite with coverage (after installing test dependencies)
poetry run pytest

# Or directly with pytest (if test dependencies are installed)
pytest

# Run without coverage (if pytest-cov is not installed)
pytest --no-cov
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# CORS-specific tests
pytest -m cors

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test specific functionality
pytest tests/test_models.py
pytest tests/test_cors.py
pytest tests/test_e2e.py

# Run with verbose output
pytest tests/test_server.py -v

# Run single test
pytest tests/test_models.py::test_wallet_type_enum -v
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=xian_uwp --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=xian_uwp --cov-report=html
# View: open htmlcov/index.html
```

## 🏗️ Test Framework

### Async Test Support

All async tests use `pytest-asyncio` with automatic mode:

```python
import pytest

async def test_async_functionality():
    """Async tests work automatically."""
    result = await some_async_function()
    assert result is not None
```

### Fixtures

Common test fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def mock_wallet():
    """Mock wallet instance for testing."""
    return MockWallet()

@pytest.fixture
async def test_server():
    """Test server with cleanup."""
    server = create_test_server()
    yield server
    await server.cleanup()
```

### Test Server Management

Tests use a managed test server approach:

```python
class TestServer:
    """Managed test server with automatic cleanup."""
    
    async def start(self, port: int = 0) -> int:
        """Start server on available port."""
        
    async def stop(self):
        """Clean shutdown."""
```

## 📋 Test Guidelines

### Writing Tests

1. **Use descriptive names**: `test_cors_allows_specific_origins_only()`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per test** when possible
4. **Use appropriate markers**: `@pytest.mark.unit`, etc.
5. **Mock external dependencies**: Use `pytest-mock`

### Example Test Structure

```python
import pytest
from xian_uwp import CORSConfig, create_server

class TestCORSConfiguration:
    """Test CORS configuration functionality."""
    
    @pytest.mark.unit
    def test_production_cors_config(self):
        """Test production CORS configuration."""
        # Arrange
        origins = ["https://mydapp.com"]
        
        # Act
        config = CORSConfig.production(origins)
        
        # Assert
        assert config.allow_origins == origins
        assert config.allow_credentials is True
    
    @pytest.mark.integration
    async def test_cors_preflight_request(self, test_server):
        """Test CORS preflight request handling."""
        # Arrange
        origin = "https://mydapp.com"
        
        # Act
        response = await test_server.options(
            "/api/v1/wallet/status",
            headers={"Origin": origin}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
```

### Async Test Patterns

```python
# Simple async test
async def test_async_client():
    async with AsyncClient() as client:
        response = await client.get("/status")
        assert response.status_code == 200

# Async fixture usage
async def test_with_server(test_server):
    response = await test_server.get("/api/v1/wallet/status")
    assert response.json()["available"] is True
```

## 🔧 Test Configuration

### pytest.ini Options

Key configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"              # Automatic async test detection
testpaths = ["tests"]              # Test discovery path
addopts = ["-v", "--cov=xian_uwp"] # Default options
```

### Environment Variables

Tests can use environment variables for configuration:

```bash
# Test with different port
XIAN_UWP_TEST_PORT=8546 pytest

# Enable debug logging
XIAN_UWP_DEBUG=1 pytest

# Test with specific network
XIAN_UWP_NETWORK=testnet pytest
```

## 🐛 Debugging Tests

### Verbose Output

```bash
# Show detailed test output
pytest -v -s

# Show print statements
pytest -s tests/test_specific.py

# Show full tracebacks
pytest --tb=long
```

### Debug Specific Tests

```bash
# Run single test with debugging
pytest tests/test_cors.py::test_specific_function -v -s

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb
```

### Common Issues

1. **Coverage errors** (`unrecognized arguments: --cov=xian_uwp`):
   ```bash
   # Solution: Install test dependencies first
   poetry install --with test
   # Or: pip install pytest-cov pytest-asyncio pytest-mock
   ```

2. **Port conflicts**: Tests use random ports to avoid conflicts

3. **Async cleanup**: All async resources are properly cleaned up

4. **Mock isolation**: Each test gets fresh mocks

5. **Server lifecycle**: Test servers are started/stopped per test

## 📊 Test Metrics

### Coverage Goals

- **Unit tests**: > 95% coverage
- **Integration tests**: > 85% coverage
- **Overall**: > 90% coverage

### Performance Targets

- **Unit tests**: < 1s each
- **Integration tests**: < 5s each
- **E2E tests**: < 30s each
- **Full suite**: < 2 minutes

## 🔄 Continuous Integration

Tests are designed to run reliably in CI environments:

- **No external dependencies**: All external services are mocked
- **Deterministic**: Tests produce consistent results
- **Parallel-safe**: Tests can run in parallel without conflicts
- **Resource cleanup**: All resources are properly cleaned up

### CI Commands

```bash
# CI test run
pytest --cov=xian_uwp --cov-report=xml --junitxml=test-results.xml

# Quick CI run (skip slow tests)
pytest -m "not slow" --cov=xian_uwp
```

---

**Happy Testing!** 🧪✨

For questions or issues with tests, check the main project documentation or open an issue.