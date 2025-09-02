#!/usr/bin/env python3
"""
Basic CLI DApp for Xian UWP
A simple command-line DApp that connects to wallets via the Xian Universal Wallet Protocol
"""

import asyncio
import json
import sys
import os
from typing import Optional, Dict, Any
import argparse

# Add reference implementation to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'reference/python'))

from xian_uwp.client import XianWalletClient
from xian_uwp.models import Permission


class CLIDApp:
    """Command-line DApp implementation"""
    
    def __init__(self, app_name: str = "CLI DApp", wallet_url: str = "http://localhost:8545"):
        self.app_name = app_name
        self.wallet_url = wallet_url
        self.client = None
        self.connected = False
        
    async def connect_wallet(self):
        """Connect to a wallet server"""
        print(f"🔌 Connecting to wallet at {self.wallet_url}...")
        
        self.client = XianWalletClient(
            app_name=self.app_name,
            app_url="http://localhost:3000",  # Dummy URL for CLI app
            server_url=self.wallet_url,
            permissions=[
                Permission.WALLET_INFO,
                Permission.BALANCE,
                Permission.TRANSACTIONS,
                Permission.SIGN_MESSAGE
            ]
        )
        
        try:
            connected = await self.client.connect()
            if connected:
                self.connected = True
                print(f"✅ Connected to wallet!")
                
                # Get wallet info
                wallet_info = await self.client.get_wallet_info()
                print(f"   Wallet type: {wallet_info.wallet_type}")
                print(f"   Address: {wallet_info.truncated_address}")
                print(f"   Network: {wallet_info.network}")
                return True
            else:
                print("❌ Failed to connect to wallet")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    async def disconnect_wallet(self):
        """Disconnect from wallet"""
        if self.client:
            await self.client.disconnect()
            self.connected = False
            print("🔌 Disconnected from wallet")
    
    async def get_wallet_info(self):
        """Get wallet information"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        try:
            info = await self.client.get_wallet_info()
            print(f"\n📋 Wallet Information:")
            print(f"   Address: {info.address}")
            print(f"   Type: {info.wallet_type}")
            print(f"   Network: {info.network}")
            print(f"   Chain ID: {info.chain_id}")
            print(f"   Locked: {info.locked}")
            return info
            
        except Exception as e:
            print(f"❌ Failed to get wallet info: {e}")
            return None
    
    async def check_balance(self, contract: str = "currency"):
        """Check token balance"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        try:
            balance = await self.client.get_balance(contract)
            symbol = "XIAN" if contract == "currency" else contract.upper()
            print(f"💰 Balance: {balance} {symbol}")
            return balance
            
        except Exception as e:
            print(f"❌ Failed to get balance: {e}")
            return None
    
    async def send_transaction(self, to: str, amount: float, contract: str = "currency"):
        """Send a transaction through the wallet"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        try:
            print(f"📤 Sending {amount} tokens to {to}...")
            print("   ⏳ Waiting for wallet approval...")
            
            result = await self.client.send_transaction(
                contract=contract,
                function="transfer",
                kwargs={"to": to, "amount": amount},
                stamps_supplied=50000
            )
            
            if result.success:
                print(f"✅ Transaction successful!")
                print(f"   Hash: {result.transaction_hash}")
                print(f"   Gas used: {result.gas_used}")
                return result
            else:
                print(f"❌ Transaction failed")
                return None
                
        except Exception as e:
            print(f"❌ Transaction error: {e}")
            return None
    
    async def sign_message(self, message: str):
        """Sign a message with the wallet"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        try:
            print(f"✍️  Signing message: '{message}'")
            print("   ⏳ Waiting for wallet approval...")
            
            result = await self.client.sign_message(message)
            
            print(f"✅ Message signed!")
            print(f"   Signature: {result.signature}")
            print(f"   Signer: {result.address}")
            return result
            
        except Exception as e:
            print(f"❌ Signing error: {e}")
            return None
    
    async def demo_defi_swap(self):
        """Demo DeFi swap interaction"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        print("\n🔄 DeFi Swap Demo")
        print("=" * 40)
        
        # Check balance first
        print("\n1️⃣ Checking XIAN balance...")
        balance = await self.check_balance("currency")
        
        if not balance or balance < 10:
            print("❌ Insufficient balance for swap demo (need at least 10 XIAN)")
            return
        
        # Simulate swap approval
        print("\n2️⃣ Requesting swap approval...")
        print("   Swapping 10 XIAN for TEST tokens")
        print("   Exchange rate: 1 XIAN = 100 TEST")
        
        # In a real DeFi app, this would call a DEX contract
        print("\n3️⃣ Executing swap transaction...")
        print("   ⏳ This is a demo - no actual swap will occur")
        
        # Sign a message to prove ownership
        swap_message = f"Approve swap: 10 XIAN for 1000 TEST at {self.app_name}"
        await self.sign_message(swap_message)
        
        print("\n✅ Swap demo completed!")
        print("   In a real DeFi app, you would now have 1000 TEST tokens")
    
    async def demo_nft_mint(self):
        """Demo NFT minting interaction"""
        if not self.connected:
            print("❌ Not connected to wallet")
            return
        
        print("\n🎨 NFT Minting Demo")
        print("=" * 40)
        
        print("\n1️⃣ Preparing NFT metadata...")
        nft_metadata = {
            "name": "Demo NFT #1",
            "description": "A demo NFT minted via CLI DApp",
            "image": "ipfs://QmDemo123",
            "attributes": [
                {"trait_type": "Rarity", "value": "Common"},
                {"trait_type": "Type", "value": "Demo"}
            ]
        }
        
        print(f"   Name: {nft_metadata['name']}")
        print(f"   Description: {nft_metadata['description']}")
        
        print("\n2️⃣ Requesting minting approval...")
        print("   Mint price: 5 XIAN")
        
        # Check balance
        balance = await self.check_balance("currency")
        if not balance or balance < 5:
            print("❌ Insufficient balance for minting (need 5 XIAN)")
            return
        
        # Sign minting request
        mint_message = f"Mint NFT: {nft_metadata['name']} for 5 XIAN"
        await self.sign_message(mint_message)
        
        print("\n✅ NFT minting demo completed!")
        print("   In a real NFT app, your NFT would now be minted on-chain")
    
    async def interactive_mode(self):
        """Run DApp in interactive mode"""
        print(f"\n🎮 {self.app_name} - Interactive Mode")
        print("=" * 40)
        
        # Connect to wallet first
        if not self.connected:
            await self.connect_wallet()
            if not self.connected:
                print("❌ Cannot proceed without wallet connection")
                return
        
        while True:
            print("\nOptions:")
            print("1. Get wallet info")
            print("2. Check balance")
            print("3. Send transaction")
            print("4. Sign message")
            print("5. Demo: DeFi Swap")
            print("6. Demo: NFT Minting")
            print("7. Disconnect & Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                await self.get_wallet_info()
                
            elif choice == "2":
                contract = input("Contract (default: currency): ").strip() or "currency"
                await self.check_balance(contract)
                
            elif choice == "3":
                to = input("Recipient address: ").strip()
                amount = float(input("Amount: ").strip())
                contract = input("Contract (default: currency): ").strip() or "currency"
                await self.send_transaction(to, amount, contract)
                
            elif choice == "4":
                message = input("Message to sign: ").strip()
                await self.sign_message(message)
                
            elif choice == "5":
                await self.demo_defi_swap()
                
            elif choice == "6":
                await self.demo_nft_mint()
                
            elif choice == "7":
                await self.disconnect_wallet()
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid option")


async def main():
    parser = argparse.ArgumentParser(description="Xian CLI DApp")
    parser.add_argument("--name", default="CLI DApp", help="DApp name")
    parser.add_argument("--wallet-url", default="http://localhost:8545", help="Wallet server URL")
    parser.add_argument("--info", action="store_true", help="Get wallet info")
    parser.add_argument("--balance", action="store_true", help="Check balance")
    parser.add_argument("--send", nargs=2, metavar=("TO", "AMOUNT"), help="Send transaction")
    parser.add_argument("--sign", help="Sign a message")
    parser.add_argument("--demo-defi", action="store_true", help="Run DeFi demo")
    parser.add_argument("--demo-nft", action="store_true", help="Run NFT demo")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    # Initialize DApp
    dapp = CLIDApp(app_name=args.name, wallet_url=args.wallet_url)
    
    # Connect to wallet
    connected = await dapp.connect_wallet()
    if not connected:
        print("❌ Failed to connect to wallet. Make sure wallet server is running.")
        sys.exit(1)
    
    try:
        # Handle commands
        if args.info:
            await dapp.get_wallet_info()
            
        elif args.balance:
            await dapp.check_balance()
            
        elif args.send:
            to, amount = args.send
            await dapp.send_transaction(to, float(amount))
            
        elif args.sign:
            await dapp.sign_message(args.sign)
            
        elif args.demo_defi:
            await dapp.demo_defi_swap()
            
        elif args.demo_nft:
            await dapp.demo_nft_mint()
            
        elif args.interactive:
            await dapp.interactive_mode()
            
        else:
            # Default: show connection info
            print(f"\n✅ Connected to wallet at {args.wallet_url}")
            print(f"   Use --help to see available commands")
            print(f"   Use --interactive for interactive mode")
            
    finally:
        # Always disconnect when done
        await dapp.disconnect_wallet()


if __name__ == "__main__":
    asyncio.run(main())