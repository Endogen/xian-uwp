"""
Example: Wallet Discovery using mDNS and Registry
Demonstrates how to discover available wallets on the network
"""

import asyncio
import httpx
from typing import List, Dict, Any


class WalletDiscovery:
    """Discover Xian wallets using various methods"""
    
    def __init__(self, registry_url: str = "https://registry.xian.org"):
        self.registry_url = registry_url
        self.local_port = 8545
        
    async def discover_mdns(self) -> List[Dict[str, Any]]:
        """Discover wallets using mDNS/Bonjour on local network"""
        # In a real implementation, use zeroconf library
        # This is a simplified example
        wallets = []
        
        # Check common local ports
        for port in [8545, 8546, 8547]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:{port}/api/v1/wallet/status",
                        timeout=1.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        wallets.append({
                            "wallet_id": f"local-{port}",
                            "name": f"Local Wallet (port {port})",
                            "type": data.get("wallet_type", "desktop"),
                            "endpoint": f"http://localhost:{port}/api/v1",
                            "version": data.get("version", "2.0.0")
                        })
            except:
                continue
                
        return wallets
    
    async def discover_registry(self) -> List[Dict[str, Any]]:
        """Query the central registry for registered wallets"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.registry_url}/api/v1/discovery/wallets"
                )
                if response.status_code == 200:
                    return response.json().get("wallets", [])
        except Exception as e:
            print(f"Registry discovery failed: {e}")
        return []
    
    async def discover_browser(self) -> List[Dict[str, Any]]:
        """Detect browser extension wallets"""
        # This would typically be done in JavaScript
        # checking for window.xianWallet or similar
        return []
    
    async def discover_all(self) -> List[Dict[str, Any]]:
        """Discover wallets using all available methods"""
        tasks = [
            self.discover_mdns(),
            self.discover_registry(),
            self.discover_browser()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        wallets = []
        
        for result in results:
            if isinstance(result, list):
                wallets.extend(result)
                
        # Remove duplicates based on wallet_id
        seen = set()
        unique_wallets = []
        for wallet in wallets:
            if wallet["wallet_id"] not in seen:
                seen.add(wallet["wallet_id"])
                unique_wallets.append(wallet)
                
        return unique_wallets


async def main():
    """Example usage of wallet discovery"""
    discovery = WalletDiscovery()
    
    print("🔍 Discovering wallets...")
    print("-" * 50)
    
    # Discover all available wallets
    wallets = await discovery.discover_all()
    
    if not wallets:
        print("No wallets found. Make sure a wallet is running.")
        return
    
    print(f"Found {len(wallets)} wallet(s):\n")
    
    for i, wallet in enumerate(wallets, 1):
        print(f"{i}. {wallet['name']}")
        print(f"   Type: {wallet['type']}")
        print(f"   Endpoint: {wallet['endpoint']}")
        print(f"   Version: {wallet.get('version', 'unknown')}")
        print(f"   Capabilities: {', '.join(wallet.get('capabilities', []))}")
        print()
    
    # Connect to the first wallet
    if wallets:
        wallet = wallets[0]
        print(f"Connecting to {wallet['name']}...")
        
        async with httpx.AsyncClient(base_url=wallet['endpoint']) as client:
            # Request authorization
            auth_response = await client.post(
                "/auth/request",
                json={
                    "app_name": "Discovery Example",
                    "app_url": "https://example.com",
                    "permissions": ["wallet_info", "balance"]
                }
            )
            
            if auth_response.status_code == 202:
                data = auth_response.json()
                print(f"✅ Authorization requested: {data['request_id']}")
                print("Check your wallet to approve the connection.")
            else:
                print(f"❌ Authorization failed: {auth_response.text}")


if __name__ == "__main__":
    asyncio.run(main())