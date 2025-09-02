#!/usr/bin/env python3
"""
Simple test wallet server for validator testing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'reference/python'))

import asyncio
from xian_py.wallet import Wallet
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType

async def main():
    # Create a test wallet with the provided private key
    private_key = "5c3c49b350dc32a7eb595429182a6135af95e90b55fe1485b2d26f13c9d19679"
    wallet = Wallet(private_key)
    
    print(f"🔑 Wallet initialized:")
    print(f"   Public Key: {wallet.public_key}")
    print(f"   Address: {wallet.public_key}")  # In Xian, address is the public key
    
    # Create and configure the server
    server = WalletProtocolServer(
        wallet_type=WalletType.CLI,
        wallet=wallet
    )
    
    # Configure network
    server.configure_network(
        network_url="https://testnet.xian.org",
        chain_id="xian-testnet-1"
    )
    
    # Start the server
    print("\n🚀 Starting wallet server on http://localhost:8545")
    print("   Press Ctrl+C to stop\n")
    
    await server.start_async(host="localhost", port=8545)
    
    try:
        # Keep the server running
        while server.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        await server.stop_async()

if __name__ == "__main__":
    asyncio.run(main())