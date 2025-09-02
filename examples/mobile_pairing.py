"""
Example: Mobile Wallet Pairing via QR Code
Demonstrates how to pair a DApp with a mobile wallet using QR codes
"""

import asyncio
import json
import base64
import qrcode
from typing import Optional
import httpx
import websockets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization


class MobileWalletPairing:
    """Handle mobile wallet pairing via QR code and relay server"""
    
    def __init__(self, relay_url: str = "wss://relay.xian.org"):
        self.relay_url = relay_url
        self.private_key = None
        self.public_key = None
        self.session_id = None
        self.paired_wallet_key = None
        
    def generate_keypair(self):
        """Generate RSA keypair for E2E encryption"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        pem = self.public_key.public_key_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(pem).decode('utf-8')
    
    async def create_pairing_request(self, app_name: str, app_url: str) -> dict:
        """Create a pairing request and generate QR code"""
        self.generate_keypair()
        
        # Create pairing request
        pairing_data = {
            "app_name": app_name,
            "app_url": app_url,
            "relay_url": self.relay_url,
            "permissions": ["wallet_info", "transactions"],
            "expiry_seconds": 300
        }
        
        # In a real implementation, this would call the wallet API
        # For demo, we'll create the response directly
        import uuid
        pairing_id = str(uuid.uuid4())
        
        qr_data = {
            "protocol": "xian-uwp",
            "version": "2.0.0",
            "pairing_id": pairing_id,
            "relay_url": self.relay_url,
            "public_key": self.get_public_key_pem(),
            "app_name": app_name
        }
        
        # Generate deep link
        qr_json = base64.b64encode(json.dumps(qr_data).encode()).decode()
        deep_link = f"xian-wallet://pair?data={qr_json}"
        
        return {
            "pairing_id": pairing_id,
            "qr_data": qr_data,
            "deep_link": deep_link,
            "expires_in": 300
        }
    
    def generate_qr_code(self, data: dict) -> str:
        """Generate QR code for pairing data"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(data))
        qr.make(fit=True)
        
        # Create ASCII representation for terminal
        ascii_qr = []
        matrix = qr.get_matrix()
        for row in matrix:
            ascii_row = ""
            for cell in row:
                ascii_row += "██" if cell else "  "
            ascii_qr.append(ascii_row)
        
        return "\n".join(ascii_qr)
    
    def encrypt_message(self, message: str, public_key_pem: str) -> str:
        """Encrypt message using wallet's public key"""
        # Load wallet's public key
        public_key_bytes = base64.b64decode(public_key_pem)
        public_key = serialization.load_pem_public_key(public_key_bytes)
        
        # Encrypt message
        encrypted = public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_message(self, encrypted: str) -> str:
        """Decrypt message using our private key"""
        encrypted_bytes = base64.b64decode(encrypted)
        
        decrypted = self.private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted.decode('utf-8')
    
    async def connect_relay(self, pairing_id: str):
        """Connect to relay server and wait for wallet pairing"""
        uri = f"{self.relay_url}/pair/{pairing_id}"
        
        async with websockets.connect(uri) as websocket:
            print(f"Connected to relay server: {self.relay_url}")
            print("Waiting for wallet to scan QR code...")
            
            # Wait for wallet connection
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "wallet_connected":
                    self.paired_wallet_key = data["public_key"]
                    self.session_id = data["session_id"]
                    print(f"✅ Wallet connected! Session: {self.session_id}")
                    
                    # Send acknowledgment
                    ack = {
                        "type": "pairing_complete",
                        "session_id": self.session_id,
                        "encrypted": self.encrypt_message(
                            "Pairing successful",
                            self.paired_wallet_key
                        )
                    }
                    await websocket.send(json.dumps(ack))
                    break
                    
                elif data["type"] == "error":
                    print(f"❌ Pairing error: {data['message']}")
                    break
    
    async def send_transaction(self, transaction_data: dict):
        """Send transaction through relay to paired wallet"""
        if not self.session_id or not self.paired_wallet_key:
            raise Exception("Not paired with wallet")
        
        uri = f"{self.relay_url}/session/{self.session_id}"
        
        async with websockets.connect(uri) as websocket:
            # Encrypt transaction data
            encrypted_data = self.encrypt_message(
                json.dumps(transaction_data),
                self.paired_wallet_key
            )
            
            message = {
                "type": "transaction_request",
                "session_id": self.session_id,
                "encrypted_payload": encrypted_data,
                "from": "dapp"
            }
            
            await websocket.send(json.dumps(message))
            print("Transaction sent, waiting for response...")
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data["type"] == "transaction_response":
                decrypted = self.decrypt_message(response_data["encrypted_payload"])
                result = json.loads(decrypted)
                return result
            else:
                raise Exception(f"Transaction failed: {response_data}")


async def main():
    """Example usage of mobile wallet pairing"""
    pairing = MobileWalletPairing()
    
    print("📱 Mobile Wallet Pairing Example")
    print("=" * 50)
    
    # Create pairing request
    pairing_request = await pairing.create_pairing_request(
        app_name="Example DApp",
        app_url="https://example-dapp.com"
    )
    
    print(f"Pairing ID: {pairing_request['pairing_id']}")
    print(f"Deep Link: {pairing_request['deep_link']}")
    print(f"Expires in: {pairing_request['expires_in']} seconds")
    print("\n📷 Scan this QR code with your mobile wallet:\n")
    
    # Generate and display QR code
    qr_ascii = pairing.generate_qr_code(pairing_request['qr_data'])
    print(qr_ascii)
    
    print("\n⏳ Waiting for wallet connection...")
    
    try:
        # Connect to relay and wait for pairing
        await asyncio.wait_for(
            pairing.connect_relay(pairing_request['pairing_id']),
            timeout=300
        )
        
        # Send a test transaction
        print("\n💸 Sending test transaction...")
        result = await pairing.send_transaction({
            "contract": "currency",
            "function": "transfer",
            "kwargs": {
                "to": "recipient_address",
                "amount": "100"
            }
        })
        
        print(f"Transaction result: {result}")
        
    except asyncio.TimeoutError:
        print("❌ Pairing timeout - QR code expired")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Note: This example requires additional dependencies:
    # pip install qrcode websockets cryptography
    asyncio.run(main())