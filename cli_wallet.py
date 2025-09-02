#!/usr/bin/env python3
"""
Basic CLI Wallet for Xian UWP
A simple command-line wallet that implements the Xian Universal Wallet Protocol
"""

import asyncio
import json
import sys
import os
import getpass
from typing import Optional, Dict, Any
from datetime import datetime
import argparse

# Add reference implementation to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'reference/python'))

from xian_py.wallet import Wallet
from xian_py.xian_async import XianAsync
from xian_py.transaction import (
    create_tx, 
    broadcast_tx_sync_async,
    get_nonce_async,
    simulate_tx_async
)
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType


class CLIWallet:
    """Command-line wallet implementation"""
    
    def __init__(self, private_key: Optional[str] = None):
        self.wallet = None
        self.server = None
        self.xian_client = None
        self.network_url = "https://testnet.xian.org"
        self.chain_id = "xian-testnet-1"
        self.server_port = 8545
        
        if private_key:
            self.wallet = Wallet(private_key)
            print(f"✅ Wallet loaded:")
            print(f"   Address: {self.wallet.public_key}")
        
    def create_new_wallet(self):
        """Create a new wallet with random keys"""
        self.wallet = Wallet()
        print(f"🔑 New wallet created:")
        print(f"   Private Key: {self.wallet.private_key}")
        print(f"   Public Key: {self.wallet.public_key}")
        print(f"\n⚠️  IMPORTANT: Save your private key securely! You'll need it to access your wallet.")
        
    def load_wallet(self, private_key: str):
        """Load wallet from private key"""
        try:
            self.wallet = Wallet(private_key)
            print(f"✅ Wallet loaded:")
            print(f"   Address: {self.wallet.public_key}")
        except Exception as e:
            print(f"❌ Failed to load wallet: {e}")
            sys.exit(1)
    
    async def get_balance(self):
        """Get wallet balance from the network"""
        if not self.wallet:
            print("❌ No wallet loaded")
            return
        
        if not self.xian_client:
            self.xian_client = XianAsync(self.network_url, wallet=self.wallet)
        
        try:
            # Get XIAN balance (currency contract)
            balance_response = await self.xian_client.get_balance(
                self.wallet.public_key,
                contract="currency"
            )
            
            # Handle different response formats
            if isinstance(balance_response, dict):
                if "__fixed__" in balance_response:
                    balance = float(balance_response["__fixed__"])
                else:
                    balance = balance_response.get("value", 0)
            elif isinstance(balance_response, (int, float)):
                balance = float(balance_response)
            else:
                balance = 0
                
            print(f"💰 Balance: {balance} XIAN")
            return balance
            
        except Exception as e:
            print(f"❌ Failed to get balance: {e}")
            return 0
    
    async def send_transaction(self, to: str, amount: float, stamps: int = 50000):
        """Send XIAN to another address"""
        if not self.wallet:
            print("❌ No wallet loaded")
            return
        
        if not self.xian_client:
            self.xian_client = XianAsync(self.network_url, wallet=self.wallet)
        
        try:
            print(f"📤 Sending {amount} XIAN to {to}...")
            
            # Get nonce
            nonce_response = await get_nonce_async(
                self.network_url,
                self.wallet.public_key
            )
            if isinstance(nonce_response, dict):
                nonce = nonce_response.get("nonce", 0)
            else:
                nonce = nonce_response if nonce_response else 0
            
            # Create transaction
            tx = create_tx(
                contract="currency",
                function="transfer",
                kwargs={"to": to, "amount": amount},
                nonce=nonce,
                stamps=stamps,
                chain_id=self.chain_id,
                private_key=self.wallet.private_key
            )
            
            # Simulate first
            print("🔍 Simulating transaction...")
            sim_result = await simulate_tx_async(self.network_url, tx)
            
            if sim_result.get("status") == "error":
                print(f"❌ Simulation failed: {sim_result.get('error', 'Unknown error')}")
                return None
            
            print(f"✅ Simulation successful. Stamps needed: {sim_result.get('stamps_used', 'unknown')}")
            
            # Broadcast transaction
            print("📡 Broadcasting transaction...")
            result = await broadcast_tx_sync_async(self.network_url, tx)
            
            if result.get("status") == "success":
                print(f"✅ Transaction successful!")
                print(f"   Hash: {result.get('hash')}")
                print(f"   Stamps used: {result.get('stamps_used')}")
                return result
            else:
                print(f"❌ Transaction failed: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Transaction error: {e}")
            return None
    
    async def start_server(self, auto_approve=False):
        """Start the UWP server for DApp connections"""
        if not self.wallet:
            print("❌ No wallet loaded")
            return
        
        print(f"\n🚀 Starting UWP server on port {self.server_port}...")
        if auto_approve:
            print("   ⚠️  Auto-approval enabled (for testing only!)")
        
        self.server = WalletProtocolServer(
            wallet_type=WalletType.CLI,
            wallet=self.wallet,
            auto_approve=auto_approve
        )
        
        # Set a default password for testing (in production, prompt user)
        from argon2 import PasswordHasher
        hasher = PasswordHasher()
        password_hash = hasher.hash("test123")
        self.server.set_wallet(self.wallet, password_hash)
        self.server.is_locked = False  # Start unlocked for testing
        
        self.server.configure_network(
            network_url=self.network_url,
            chain_id=self.chain_id
        )
        
        await self.server.start_async(host="localhost", port=self.server_port)
        
        print(f"✅ Server running at http://localhost:{self.server_port}")
        print(f"   DApps can now connect to your wallet")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            while self.server.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping server...")
            await self.server.stop_async()
    
    async def interactive_mode(self):
        """Run wallet in interactive mode"""
        print("\n🎮 Interactive Wallet Mode")
        print("=" * 40)
        
        while True:
            print("\nOptions:")
            print("1. Check balance")
            print("2. Send transaction")
            print("3. Start UWP server")
            print("4. Show wallet info")
            print("5. Exit")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                await self.get_balance()
                
            elif choice == "2":
                to = input("Recipient address: ").strip()
                amount = float(input("Amount (XIAN): ").strip())
                stamps = int(input("Stamps (default 50000): ").strip() or "50000")
                await self.send_transaction(to, amount, stamps)
                
            elif choice == "3":
                await self.start_server()
                
            elif choice == "4":
                if self.wallet:
                    print(f"\n📋 Wallet Info:")
                    print(f"   Address: {self.wallet.public_key}")
                    print(f"   Network: {self.network_url}")
                    print(f"   Chain ID: {self.chain_id}")
                else:
                    print("❌ No wallet loaded")
                    
            elif choice == "5":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid option")


async def main():
    parser = argparse.ArgumentParser(description="Xian CLI Wallet")
    parser.add_argument("--private-key", help="Private key to load wallet")
    parser.add_argument("--create", action="store_true", help="Create new wallet")
    parser.add_argument("--balance", action="store_true", help="Check balance")
    parser.add_argument("--send", nargs=2, metavar=("TO", "AMOUNT"), help="Send transaction")
    parser.add_argument("--server", action="store_true", help="Start UWP server")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--network", default="https://testnet.xian.org", help="Network URL")
    parser.add_argument("--port", type=int, default=8545, help="UWP server port")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve connections (testing only)")
    
    args = parser.parse_args()
    
    # Initialize wallet
    wallet = CLIWallet()
    
    if args.network:
        wallet.network_url = args.network
        
    if args.port:
        wallet.server_port = args.port
    
    # Handle wallet creation/loading
    if args.create:
        wallet.create_new_wallet()
        return
        
    if args.private_key:
        wallet.load_wallet(args.private_key)
    elif not args.create:
        # Try to load from environment variable
        pk = os.environ.get("XIAN_PRIVATE_KEY")
        if pk:
            wallet.load_wallet(pk)
        else:
            print("ℹ️  No wallet loaded. Use --private-key or set XIAN_PRIVATE_KEY env var")
            print("   Or use --create to create a new wallet")
    
    # Handle commands
    if args.balance:
        if wallet.wallet:
            await wallet.get_balance()
        else:
            print("❌ No wallet loaded")
            
    elif args.send:
        if wallet.wallet:
            to, amount = args.send
            await wallet.send_transaction(to, float(amount))
        else:
            print("❌ No wallet loaded")
            
    elif args.server:
        if wallet.wallet:
            await wallet.start_server(auto_approve=args.auto_approve)
        else:
            print("❌ No wallet loaded")
            
    elif args.interactive:
        if wallet.wallet:
            await wallet.interactive_mode()
        else:
            print("❌ No wallet loaded")
    else:
        # Default: show wallet info
        if wallet.wallet:
            print(f"\n📋 Wallet Info:")
            print(f"   Address: {wallet.wallet.public_key}")
            print(f"   Network: {wallet.network_url}")
            print(f"\nUse --help to see available commands")


if __name__ == "__main__":
    asyncio.run(main())