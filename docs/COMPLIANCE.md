# Compliance Testing Guide

This guide explains how to test your wallet implementation for compliance with the Xian Universal Wallet Protocol.

## Overview

Protocol compliance ensures that:
- Your wallet works with any UWP-compliant DApp
- DApps can rely on consistent behavior across wallets
- The ecosystem maintains interoperability

## Compliance Levels

### Level 1: Core Compliance ✅
- Implements all required endpoints
- Passes basic test vectors
- Proper error handling

### Level 2: Full Compliance ⭐
- Level 1 + all optional endpoints
- Passes all test vectors
- WebSocket support
- Performance benchmarks met

### Level 3: Certified Implementation 🏆
- Level 2 + security audit
- Production deployment verified
- Community reviewed

## Testing Process

### Step 1: Self-Testing

Run the automated test suite against your implementation:

```bash
# Clone the test suite
git clone https://github.com/xian-network/xian-uwp
cd xian-uwp/protocol

# Run basic compliance tests
python validator.py --url http://localhost:8545 --level core

# Run full compliance tests
python validator.py --url http://localhost:8545 --level full
```

### Step 2: Test Vector Validation

Each test vector in `/protocol/test-vectors/` must pass:

```python
import json
import httpx
from jsonschema import validate

def test_compliance(base_url="http://localhost:8545"):
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Test auth flow
    with open("test-vectors/auth-flow.json") as f:
        auth_vectors = json.load(f)
    
    for vector in auth_vectors["vectors"]:
        try:
            response = make_request(base_url, vector)
            validate_response(response, vector)
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "vector": vector["id"],
                "error": str(e)
            })
    
    return results
```

### Step 3: Manual Testing Checklist

#### Authorization Flow
- [ ] DApp can request authorization
- [ ] Request appears in wallet UI
- [ ] User can approve/deny request
- [ ] Session token is returned on approval
- [ ] Token works for authenticated endpoints
- [ ] Token expires after timeout
- [ ] Multiple DApps can connect simultaneously

#### Transaction Flow
- [ ] Transactions require valid session
- [ ] Insufficient permissions are rejected
- [ ] Wallet locked state is handled
- [ ] Transaction errors are properly formatted
- [ ] Gas estimation works correctly

#### Security
- [ ] Rate limiting on auth attempts
- [ ] Password attempts are limited
- [ ] Sessions expire correctly
- [ ] Invalid tokens are rejected
- [ ] CORS headers are present

## Test Vectors

### Understanding Test Vector Format

```json
{
  "id": "auth-001",
  "description": "Valid authorization request",
  "request": {
    "method": "POST",
    "path": "/api/v1/auth/request",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "app_name": "Test DApp",
      "app_url": "https://test.com",
      "permissions": ["wallet_info"]
    }
  },
  "response": {
    "status": 202,
    "body": {
      "request_id": "STRING:REGEX:^[a-zA-Z0-9_-]{16,}$",
      "status": "pending"
    }
  }
}
```

### Response Validation Rules

- `STRING`: Must be a string
- `NUMBER`: Must be a number
- `BOOLEAN`: Must be a boolean
- `ARRAY`: Must be an array
- `OBJECT`: Must be an object
- `STRING:REGEX:pattern`: String matching regex
- `OPTIONAL`: Field may be absent
- `ANY`: Any type accepted

## Automated Validator

### Installation

```bash
pip install httpx jsonschema pyyaml
```

### Basic Usage

```python
from xian_uwp_validator import ProtocolValidator

validator = ProtocolValidator("http://localhost:8545")
results = validator.run_compliance_suite()

print(f"Compliance: {results['compliant']}")
print(f"Passed: {results['passed']}/{results['total']}")

if not results['compliant']:
    for error in results['errors']:
        print(f"❌ {error['test']}: {error['message']}")
```

### Custom Test Cases

```python
# Add custom test cases for your implementation
custom_tests = [
    {
        "name": "Custom feature test",
        "request": {
            "method": "GET",
            "path": "/api/v1/x/my-feature"
        },
        "response": {
            "status": 200
        }
    }
]

validator.add_custom_tests(custom_tests)
results = validator.run_compliance_suite()
```

## Performance Benchmarks

Compliant implementations should meet these benchmarks:

| Endpoint | Response Time (p95) | Throughput |
|----------|-------------------|------------|
| `/wallet/status` | < 50ms | > 1000 req/s |
| `/auth/request` | < 100ms | > 100 req/s |
| `/transaction` | < 500ms | > 50 req/s |
| `/balance/*` | < 200ms | > 200 req/s |

### Running Performance Tests

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8545/api/v1/wallet/status

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8545/api/v1/wallet/status
```

## Security Testing

### OWASP Top 10 Checklist

- [ ] **Injection**: Validate all inputs against schemas
- [ ] **Broken Authentication**: Secure token generation
- [ ] **Sensitive Data Exposure**: No logging of tokens/passwords
- [ ] **XML External Entities**: N/A (JSON only)
- [ ] **Broken Access Control**: Permission validation
- [ ] **Security Misconfiguration**: Secure defaults
- [ ] **XSS**: N/A (API only)
- [ ] **Insecure Deserialization**: JSON validation
- [ ] **Using Components with Known Vulnerabilities**: Keep dependencies updated
- [ ] **Insufficient Logging**: Log security events

### Security Test Script

```python
import httpx
import time

def test_rate_limiting(base_url):
    """Test rate limiting on sensitive endpoints"""
    client = httpx.Client(base_url=base_url)
    
    # Test unlock endpoint
    for i in range(10):
        response = client.post("/api/v1/wallet/unlock", 
                              json={"password": "wrong"})
        if response.status_code == 429:
            print(f"✅ Rate limiting triggered after {i+1} attempts")
            return True
    
    print("❌ No rate limiting detected")
    return False

def test_token_entropy(base_url):
    """Test session token randomness"""
    tokens = set()
    
    for _ in range(100):
        # Request authorization and collect tokens
        # Check for duplicates or patterns
        pass
    
    return len(tokens) == 100  # All unique

def test_cors_headers(base_url):
    """Test CORS configuration"""
    response = httpx.options(f"{base_url}/api/v1/wallet/status")
    headers = response.headers
    
    required = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers"
    ]
    
    return all(h in headers for h in required)
```

## Submission Process

### 1. Prepare Your Implementation

- [ ] All tests passing
- [ ] Documentation complete
- [ ] Security considerations addressed
- [ ] Performance benchmarks met

### 2. Create Compliance Report

```markdown
# Compliance Report - [Your Wallet Name]

## Implementation Details
- **Language**: [e.g., Rust]
- **Framework**: [e.g., Actix-web]
- **Version**: [e.g., 1.0.0]
- **Repository**: [GitHub URL]

## Test Results
- Core Compliance: ✅ PASS (50/50 tests)
- Full Compliance: ✅ PASS (75/75 tests)
- Performance: ✅ PASS (all benchmarks met)
- Security: ✅ PASS (OWASP checklist complete)

## Additional Features
- [List any extensions or custom features]

## Known Limitations
- [List any limitations or caveats]
```

### 3. Submit for Review

1. Fork the xian-uwp repository
2. Add your implementation to `/implementations/[language]/`
3. Include compliance report
4. Submit pull request

## Troubleshooting

### Common Compliance Issues

#### Issue: "Invalid JSON response"
**Solution**: Ensure all responses are valid JSON with correct Content-Type header

#### Issue: "Session token format invalid"
**Solution**: Tokens must be at least 32 bytes (256 bits) of entropy

#### Issue: "CORS headers missing"
**Solution**: Add required CORS headers for all endpoints

#### Issue: "Rate limiting not detected"
**Solution**: Implement rate limiting on sensitive endpoints

## Certification

Implementations that pass all compliance tests can apply for official certification:

1. **Submit compliance report**
2. **Undergo security review**
3. **Deploy to production**
4. **Receive certification badge**

Certified implementations are listed in the official registry and receive a verification badge.

## Support

- [GitHub Issues](https://github.com/xian-network/xian-uwp/issues)
- [Discord #wallet-protocol](https://discord.gg/xian)
- [Protocol Discussions](https://github.com/xian-network/xian-uwp/discussions)