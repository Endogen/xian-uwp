#!/usr/bin/env python3
"""
Test the full flow of the Xian UWP implementation
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

class UWPTester:
    def __init__(self, wallet_url: str = "http://localhost:8545"):
        self.wallet_url = wallet_url
        self.session_token = None
        self.request_id = None
        
    async def test_info(self):
        """Test wallet status endpoint"""
        print("\n📋 Testing wallet status...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.wallet_url}/api/v1/wallet/status")
            assert response.status_code == 200
            data = response.json()
            print(f"   ✅ Wallet: {data['wallet_type']} v{data['version']}")
            print(f"   ✅ Network: {data['network']}")
            print(f"   ✅ Chain: {data['chain_id']}")
            print(f"   ✅ Locked: {data['locked']}")
            return True
            
    async def test_unlock_wallet(self):
        """Test wallet unlock"""
        print("\n🔓 Testing wallet unlock...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.wallet_url}/api/v1/wallet/unlock",
                json={"password": "test123"}  # Default password from CLI wallet
            )
            if response.status_code == 200:
                print(f"   ✅ Wallet unlocked successfully")
                return True
            else:
                print(f"   ❌ Failed to unlock: {response.status_code}")
                if response.status_code == 400:
                    print(f"      Error: {response.json()}")
                return False
    
    async def test_auth_flow(self):
        """Test authorization flow"""
        print("\n🔐 Testing authorization flow...")
        
        # Request authorization
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.wallet_url}/api/v1/auth/request",
                json={
                    "app_name": "Test DApp",
                    "app_url": "https://testdapp.example.com",
                    "permissions": ["wallet_info", "balance", "transactions"],
                    "description": "Test application for UWP validation"
                }
            )
            if response.status_code != 202:
                print(f"   ❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text}")
            assert response.status_code == 202
            data = response.json()
            self.request_id = data["request_id"]
            print(f"   ✅ Authorization requested: {self.request_id}")
            
            # Check if auto-approved
            if data.get("status") == "approved":
                self.session_token = data.get("session_token")
                print(f"   ✅ Auto-approved! Session token received")
                return True
            
            # Wait for approval (manual flow)
            print("   ⏳ Waiting for manual approval...")
            for i in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                response = await client.get(
                    f"{self.wallet_url}/api/v1/auth/status/{self.request_id}"
                )
                if response.status_code == 200:
                    status_data = response.json()
                    if status_data.get("status") == "approved":
                        # Need to get session token from somewhere
                        print("   ✅ Approved!")
                        return True
                elif response.status_code == 404:
                    # Check if it was approved (session exists)
                    print("   ✅ Request approved (not found in pending)")
                    return True
            
            print("   ❌ Timeout waiting for approval")
            return False
            
    async def test_wallet_info_with_auth(self):
        """Test authenticated wallet info"""
        if not self.session_token:
            print("\n⚠️  Skipping authenticated tests (no session)")
            return False
            
        print("\n💳 Testing authenticated wallet info...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.wallet_url}/api/v1/wallet/info",
                headers={"Authorization": f"Bearer {self.session_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Address: {data['address']}")
                if 'public_key' in data:
                    print(f"   ✅ Public Key: {data['public_key'][:20]}...")
                return True
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return False
                
    async def test_balance(self):
        """Test balance check"""
        if not self.session_token:
            print("\n⚠️  Skipping balance test (no session)")
            return False
            
        print("\n💰 Testing balance check...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.wallet_url}/api/v1/balance/currency",
                headers={"Authorization": f"Bearer {self.session_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Balance: {data.get('balance', 0)} XIAN")
                return True
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return False
                
    async def test_transaction(self):
        """Test transaction endpoint (dry run)"""
        if not self.session_token:
            print("\n⚠️  Skipping transaction test (no session)")
            return False
            
        print("\n📤 Testing transaction endpoint...")
        async with httpx.AsyncClient() as client:
            # Test with a small amount to avoid actually spending funds
            response = await client.post(
                f"{self.wallet_url}/api/v1/transaction",
                headers={"Authorization": f"Bearer {self.session_token}"},
                json={
                    "contract": "currency",
                    "function": "transfer",
                    "kwargs": {
                        "to": "test_recipient_address_1234567890abcdef",
                        "amount": 0.00001  # Very small amount
                    }
                }
            )
            
            # We expect this might fail due to insufficient balance or invalid address
            # but we're testing that the endpoint works
            if response.status_code in [200, 400]:
                data = response.json()
                if response.status_code == 200:
                    print(f"   ✅ Transaction successful")
                    print(f"   ✅ Hash: {data.get('transaction_hash', 'N/A')}")
                else:
                    print(f"   ⚠️  Transaction failed (expected): {data.get('error', 'Unknown error')}")
                return True
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                return False
                
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting UWP Full Flow Test")
        print("=" * 50)
        
        results = []
        
        # Basic tests
        results.append(await self.test_info())
        results.append(await self.test_unlock_wallet())
        results.append(await self.test_auth_flow())
        
        # Authenticated tests
        results.append(await self.test_wallet_info_with_auth())
        results.append(await self.test_balance())
        results.append(await self.test_transaction())
        
        # Summary
        print("\n" + "=" * 50)
        passed = sum(1 for r in results if r)
        total = len(results)
        
        if passed == total:
            print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        else:
            print(f"❌ SOME TESTS FAILED ({passed}/{total})")
            
        return passed == total

async def main():
    # Test with auto-approve server
    print("\n🔧 Testing with auto-approve enabled...")
    print("Please ensure the wallet server is running with --auto-approve flag")
    
    tester = UWPTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 Implementation is working correctly!")
    else:
        print("\n⚠️  Some issues found, please review")
        
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)