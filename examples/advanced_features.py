#!/usr/bin/env python3
"""
Example demonstrating advanced features of the Xian Wallet Protocol:
- WebSocket authentication
- Refresh tokens
- DApp identity verification
"""

import asyncio
import json
import secrets
import websockets
from datetime import datetime
from typing import Optional

import httpx


class AdvancedWalletClient:
    """Client demonstrating advanced wallet protocol features"""
    
    def __init__(self, wallet_url: str = "http://localhost:8545"):
        self.wallet_url = wallet_url
        self.session_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.dapp_id: Optional[str] = None
        
    async def register_dapp(self, app_name: str, app_url: str, public_key: str):
        """Register DApp for identity verification"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.wallet_url}/api/v1/dapp/register",
                json={
                    "app_name": app_name,
                    "app_url": app_url,
                    "public_key": public_key,
                    "algorithm": "ed25519",
                    "metadata": {
                        "description": "Example DApp demonstrating advanced features",
                        "categories": ["Example", "Demo"]
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.dapp_id = data["dapp_id"]
                print(f"✅ DApp registered: {self.dapp_id}")
                
                # Verify the DApp (simplified - in production, sign the challenge)
                await self.verify_dapp(data.get("challenge"))
                return self.dapp_id
            else:
                print(f"❌ DApp registration failed: {response.text}")
                return None
    
    async def verify_dapp(self, challenge: str):
        """Verify DApp signature"""
        if not self.dapp_id:
            return
        
        async with httpx.AsyncClient() as client:
            # In production, sign the challenge with your private key
            signature = "example_signature_" + secrets.token_hex(32)
            
            response = await client.post(
                f"{self.wallet_url}/api/v1/dapp/verify",
                json={
                    "dapp_id": self.dapp_id,
                    "message": challenge,
                    "signature": signature
                }
            )
            
            if response.status_code == 200:
                print(f"✅ DApp verified: {self.dapp_id}")
            else:
                print(f"❌ DApp verification failed: {response.text}")
    
    async def request_authorization_with_signature(self, app_name: str, app_url: str, permissions: list):
        """Request authorization with DApp signature"""
        async with httpx.AsyncClient() as client:
            # Prepare signed request
            timestamp = int(datetime.now().timestamp())
            message = f"{app_name}{app_url}{''.join(permissions)}{timestamp}"
            
            # In production, sign the message with your private key
            signature = "example_signature_" + secrets.token_hex(32)
            
            request_data = {
                "app_name": app_name,
                "app_url": app_url,
                "permissions": permissions,
                "description": "Advanced features demo"
            }
            
            # Add DApp verification if registered
            if self.dapp_id:
                request_data.update({
                    "dapp_id": self.dapp_id,
                    "signature": signature,
                    "timestamp": timestamp
                })
            
            response = await client.post(
                f"{self.wallet_url}/api/v1/auth/request",
                json=request_data
            )
            
            if response.status_code == 202:
                data = response.json()
                print(f"✅ Authorization requested: {data['request_id']}")
                return data["request_id"]
            else:
                print(f"❌ Authorization request failed: {response.text}")
                return None
    
    async def wait_for_approval(self, request_id: str) -> bool:
        """Wait for authorization approval and store tokens"""
        async with httpx.AsyncClient() as client:
            for _ in range(60):  # Wait up to 60 seconds
                response = await client.get(
                    f"{self.wallet_url}/api/v1/auth/status/{request_id}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data["status"] == "approved":
                        self.session_token = data["session_token"]
                        self.refresh_token = data.get("refresh_token")
                        
                        print(f"✅ Authorization approved!")
                        print(f"   Session token: {self.session_token[:20]}...")
                        if self.refresh_token:
                            print(f"   Refresh token: {self.refresh_token[:20]}...")
                        return True
                    
                    elif data["status"] == "denied":
                        print("❌ Authorization denied")
                        return False
                
                await asyncio.sleep(1)
            
            print("⏱️ Authorization timeout")
            return False
    
    async def refresh_session(self):
        """Refresh the session using refresh token"""
        if not self.refresh_token:
            print("❌ No refresh token available")
            return False
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.wallet_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data["session_token"]
                
                # Update refresh token if rotated
                if data.get("refresh_token"):
                    self.refresh_token = data["refresh_token"]
                
                print(f"✅ Session refreshed!")
                print(f"   New session token: {self.session_token[:20]}...")
                if data.get("refresh_token"):
                    print(f"   New refresh token: {self.refresh_token[:20]}...")
                return True
            else:
                print(f"❌ Session refresh failed: {response.text}")
                return False
    
    async def connect_websocket(self):
        """Connect to WebSocket with authentication"""
        if not self.session_token:
            print("❌ No session token available")
            return
        
        # Connect with token in query parameter
        ws_url = f"ws://localhost:8545/ws/v1?token={self.session_token}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connected with authentication")
                
                # Send ping
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Receive pong
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "pong":
                    print("✅ WebSocket ping/pong successful")
                
                # Keep connection alive for a bit
                await asyncio.sleep(2)
                
        except websockets.exceptions.WebSocketException as e:
            print(f"❌ WebSocket connection failed: {e}")
    
    async def get_wallet_info(self):
        """Get wallet info using session token"""
        if not self.session_token:
            print("❌ No session token available")
            return
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.wallet_url}/api/v1/wallet/info",
                headers={"Authorization": f"Bearer {self.session_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Wallet info retrieved:")
                print(f"   Address: {data['address']}")
                print(f"   Type: {data['wallet_type']}")
                return data
            else:
                print(f"❌ Failed to get wallet info: {response.text}")
                return None


async def main():
    """Demonstrate advanced wallet protocol features"""
    print("🚀 Xian Wallet Protocol - Advanced Features Demo\n")
    
    client = AdvancedWalletClient()
    
    # Step 1: Register DApp (optional)
    print("1️⃣ Registering DApp...")
    public_key = "0x" + secrets.token_hex(32)  # Example public key
    await client.register_dapp(
        app_name="Advanced Demo App",
        app_url="https://demo.example.com",
        public_key=public_key
    )
    print()
    
    # Step 2: Request authorization with signature
    print("2️⃣ Requesting authorization with DApp signature...")
    request_id = await client.request_authorization_with_signature(
        app_name="Advanced Demo App",
        app_url="https://demo.example.com",
        permissions=["wallet_info", "balance"]
    )
    print()
    
    if request_id:
        # Step 3: Wait for approval
        print("3️⃣ Waiting for user approval...")
        print("   ⚠️ Please approve the request in your wallet")
        approved = await client.wait_for_approval(request_id)
        print()
        
        if approved:
            # Step 4: Use the session
            print("4️⃣ Using authenticated session...")
            await client.get_wallet_info()
            print()
            
            # Step 5: Connect WebSocket with authentication
            print("5️⃣ Connecting to WebSocket with authentication...")
            await client.connect_websocket()
            print()
            
            # Step 6: Refresh the session
            if client.refresh_token:
                print("6️⃣ Refreshing session with refresh token...")
                await asyncio.sleep(2)  # Simulate some time passing
                await client.refresh_session()
                print()
                
                # Use the new session
                print("7️⃣ Using refreshed session...")
                await client.get_wallet_info()
            else:
                print("ℹ️ Refresh tokens not available")
    
    print("\n✨ Advanced features demo complete!")


if __name__ == "__main__":
    asyncio.run(main())