#!/usr/bin/env python3
"""
Xian Universal Wallet Protocol - Compliance Validator

Usage:
    python validator.py --url http://localhost:8545 --level core
    python validator.py --url http://localhost:8545 --level full --verbose
"""

import json
import sys
import time
import argparse
import re
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

try:
    import httpx
    import jsonschema
except ImportError:
    print("Please install required packages: pip install httpx jsonschema")
    sys.exit(1)


class ProtocolValidator:
    """Validates protocol compliance for wallet implementations"""
    
    def __init__(self, base_url: str = "http://localhost:8545", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.client = httpx.Client(timeout=10.0)
        self.results = {
            "compliant": True,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "errors": [],
            "warnings": []
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[{level}] {message}")
    
    def validate_response_value(self, actual: Any, expected: Any, path: str = "") -> bool:
        """Validate a response value against expected format"""
        if isinstance(expected, str):
            # Check for special validation rules
            if expected.startswith("STRING:REGEX:"):
                pattern = expected.replace("STRING:REGEX:", "")
                if not isinstance(actual, str) or not re.match(pattern, actual):
                    self.results["errors"].append(f"{path}: String doesn't match pattern {pattern}")
                    return False
                return True
            elif expected == "STRING":
                if not isinstance(actual, str):
                    self.results["errors"].append(f"{path}: Expected string, got {type(actual).__name__}")
                    return False
                return True
            elif expected == "NUMBER":
                if not isinstance(actual, (int, float)):
                    self.results["errors"].append(f"{path}: Expected number, got {type(actual).__name__}")
                    return False
                return True
            elif expected == "BOOLEAN":
                if not isinstance(actual, bool):
                    self.results["errors"].append(f"{path}: Expected boolean, got {type(actual).__name__}")
                    return False
                return True
            elif expected == "ARRAY":
                if not isinstance(actual, list):
                    self.results["errors"].append(f"{path}: Expected array, got {type(actual).__name__}")
                    return False
                return True
            elif expected == "OBJECT":
                if not isinstance(actual, dict):
                    self.results["errors"].append(f"{path}: Expected object, got {type(actual).__name__}")
                    return False
                return True
            elif expected.startswith("STRING:OPTIONAL"):
                if actual is not None and not isinstance(actual, str):
                    self.results["errors"].append(f"{path}: Expected string or null, got {type(actual).__name__}")
                    return False
                return True
            elif expected == "ANY:OPTIONAL":
                return True  # Any value including None is acceptable
            else:
                # Literal value comparison
                if actual != expected:
                    self.results["errors"].append(f"{path}: Expected '{expected}', got '{actual}'")
                    return False
                return True
        elif isinstance(expected, dict):
            if not isinstance(actual, dict):
                self.results["errors"].append(f"{path}: Expected object, got {type(actual).__name__}")
                return False
            
            # Validate each field in expected
            for key, value in expected.items():
                if key not in actual and not (isinstance(value, str) and "OPTIONAL" in value):
                    self.results["errors"].append(f"{path}.{key}: Missing required field")
                    return False
                if key in actual:
                    if not self.validate_response_value(actual[key], value, f"{path}.{key}"):
                        return False
            return True
        elif isinstance(expected, list):
            if not isinstance(actual, list):
                self.results["errors"].append(f"{path}: Expected array, got {type(actual).__name__}")
                return False
            return True
        else:
            return actual == expected
    
    def test_endpoint(self, vector: Dict) -> bool:
        """Test a single endpoint against a test vector"""
        test_id = vector.get("id", "unknown")
        description = vector.get("description", "")
        
        self.log(f"Testing {test_id}: {description}")
        
        try:
            # Prepare request
            method = vector["request"]["method"]
            path = vector["request"]["path"]
            headers = vector["request"].get("headers", {})
            body = vector["request"].get("body")
            
            # Make request
            url = f"{self.base_url}{path}"
            
            if method == "GET":
                response = self.client.get(url, headers=headers)
            elif method == "POST":
                response = self.client.post(url, headers=headers, json=body)
            else:
                self.results["errors"].append(f"{test_id}: Unsupported method {method}")
                return False
            
            # Validate response
            expected_status = vector["response"]["status"]
            if response.status_code != expected_status:
                self.results["errors"].append(
                    f"{test_id}: Expected status {expected_status}, got {response.status_code}"
                )
                return False
            
            # Validate response body if specified
            if "body" in vector["response"]:
                try:
                    actual_body = response.json()
                except json.JSONDecodeError:
                    self.results["errors"].append(f"{test_id}: Response is not valid JSON")
                    return False
                
                expected_body = vector["response"]["body"]
                if not self.validate_response_value(actual_body, expected_body, test_id):
                    return False
            
            self.log(f"✅ {test_id} passed", "SUCCESS")
            return True
            
        except httpx.RequestError as e:
            self.results["errors"].append(f"{test_id}: Request failed - {str(e)}")
            return False
        except Exception as e:
            self.results["errors"].append(f"{test_id}: Unexpected error - {str(e)}")
            return False
    
    def test_basic_connectivity(self) -> bool:
        """Test basic connectivity to the wallet server"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/wallet/status")
            if response.status_code == 200:
                data = response.json()
                if data.get("available"):
                    print(f"✅ Connected to wallet: {data.get('wallet_type', 'unknown')} v{data.get('version', 'unknown')}")
                    return True
                else:
                    print("❌ Wallet is not available")
                    return False
            else:
                print(f"❌ Failed to connect: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False
    
    def load_test_vectors(self, level: str = "core") -> List[Dict]:
        """Load test vectors based on compliance level"""
        vectors = []
        vector_dir = Path(__file__).parent / "test-vectors"
        
        if level == "core":
            # Load only essential test vectors
            files = ["auth-flow.json"]
        else:
            # Load all test vectors
            files = list(vector_dir.glob("*.json"))
            files = [f.name for f in files]
        
        for filename in files:
            filepath = vector_dir / filename
            if filepath.exists():
                with open(filepath) as f:
                    data = json.load(f)
                    vectors.extend(data.get("vectors", []))
                    self.log(f"Loaded {len(data.get('vectors', []))} vectors from {filename}")
        
        return vectors
    
    def run_compliance_suite(self, level: str = "core") -> Dict:
        """Run the complete compliance test suite"""
        print(f"\n🔍 Xian UWP Compliance Validator")
        print(f"📍 Testing: {self.base_url}")
        print(f"📊 Level: {level}\n")
        
        # Test basic connectivity
        if not self.test_basic_connectivity():
            self.results["compliant"] = False
            self.results["errors"].append("Failed to connect to wallet server")
            return self.results
        
        # Load and run test vectors
        vectors = self.load_test_vectors(level)
        self.results["total"] = len(vectors)
        
        print(f"\n📝 Running {len(vectors)} test vectors...\n")
        
        for vector in vectors:
            if self.test_endpoint(vector):
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
                self.results["compliant"] = False
        
        # Print results
        self.print_results()
        
        return self.results
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*50)
        print("📊 COMPLIANCE TEST RESULTS")
        print("="*50)
        
        if self.results["compliant"]:
            print(f"✅ COMPLIANT - All tests passed!")
        else:
            print(f"❌ NOT COMPLIANT - Some tests failed")
        
        print(f"\n📈 Statistics:")
        print(f"  • Passed: {self.results['passed']}/{self.results['total']}")
        print(f"  • Failed: {self.results['failed']}/{self.results['total']}")
        
        if self.results["failed"] > 0:
            print(f"\n❌ Failures:")
            for error in self.results["errors"][:10]:  # Show first 10 errors
                print(f"  • {error}")
            
            if len(self.results["errors"]) > 10:
                print(f"  • ... and {len(self.results['errors']) - 10} more errors")
        
        if self.results["warnings"]:
            print(f"\n⚠️  Warnings:")
            for warning in self.results["warnings"]:
                print(f"  • {warning}")
        
        print("\n" + "="*50)
        
        # Exit code
        sys.exit(0 if self.results["compliant"] else 1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Xian Universal Wallet Protocol - Compliance Validator"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8545",
        help="Wallet server URL (default: http://localhost:8545)"
    )
    parser.add_argument(
        "--level",
        choices=["core", "full"],
        default="core",
        help="Compliance level to test (default: core)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Run validator
    validator = ProtocolValidator(args.url, args.verbose)
    validator.run_compliance_suite(args.level)


if __name__ == "__main__":
    main()