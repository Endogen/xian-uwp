# Xian UWP - Python Reference Implementation

This is the reference implementation of the Xian Universal Wallet Protocol in Python.

## Installation

```bash
pip install xian-uwp
```

## Quick Start

### For Wallet Developers

```python
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType
from xian_py.wallet import Wallet

# Create your wallet instance
wallet = Wallet(seed="your_seed_phrase")

# Create and configure the protocol server
server = WalletProtocolServer(
    wallet_type=WalletType.DESKTOP,
    wallet=wallet
)

# Configure network
server.configure_network(
    network_url="https://testnet.xian.org",
    chain_id="xian-testnet-1"
)

# Set password for wallet unlock
server.set_password("secure_password")

# Start the server
server.run(host="127.0.0.1", port=8545)
```

### For DApp Developers

```python
from xian_uwp.client import XianWalletClientSync

# Connect to any wallet implementing the protocol
client = XianWalletClientSync(
    app_name="My DApp",
    app_url="https://mydapp.com"
)

# Connect and request permissions
if client.connect():
    # Get wallet info
    info = client.get_wallet_info()
    print(f"Connected to wallet: {info.address}")
    
    # Check balance
    balance = client.get_balance("currency")
    print(f"Balance: {balance}")
    
    # Send transaction
    result = client.send_transaction(
        contract="currency",
        function="transfer",
        kwargs={"to": "recipient_address", "amount": 100}
    )
    
    if result.success:
        print(f"Transaction sent: {result.transaction_hash}")
```

## Async Support

The library provides both synchronous and asynchronous clients:

```python
import asyncio
from xian_uwp.client import XianWalletClient

async def main():
    client = XianWalletClient("My DApp", "https://mydapp.com")
    
    if await client.connect():
        info = await client.get_wallet_info()
        balance = await client.get_balance("currency")
        print(f"Wallet {info.address} has balance: {balance}")

asyncio.run(main())
```

## Configuration

### CORS Configuration

For web-based DApps, configure CORS appropriately:

```python
from xian_uwp.models import CORSConfig

# Development (allows all origins)
cors_config = CORSConfig.development()

# Production (specific origins only)
cors_config = CORSConfig.production(
    allowed_origins=["https://mydapp.com", "https://app.mydapp.com"]
)

# Localhost development
cors_config = CORSConfig.localhost_dev(ports=[3000, 5173, 8080])

server = WalletProtocolServer(
    wallet_type=WalletType.DESKTOP,
    cors_config=cors_config
)
```

### Security Features

- **Password Protection**: Wallets are protected with Argon2 password hashing
- **Session Management**: Automatic session expiration and token rotation
- **Rate Limiting**: Built-in protection against brute force attacks
- **Permission System**: Granular control over DApp access

## Protocol Compliance

This implementation fully complies with the Xian Universal Wallet Protocol v2.0.0 specification.

To verify compliance:

```bash
# Run the compliance test suite
python -m xian_uwp.test_compliance
```

## API Reference

### WalletProtocolServer

Main server class for wallet implementations.

**Parameters:**
- `wallet_type`: Type of wallet (DESKTOP, WEB, CLI, HARDWARE, MOBILE)
- `cors_config`: CORS configuration for web compatibility
- `network_url`: Xian network URL
- `chain_id`: Blockchain chain ID
- `wallet`: Xian wallet instance

**Methods:**
- `configure_network(network_url, chain_id)`: Set network configuration
- `set_password(password)`: Set wallet unlock password
- `run(host="127.0.0.1", port=8545)`: Start the server
- `shutdown()`: Gracefully shutdown the server

### XianWalletClient / XianWalletClientSync

Client classes for DApp connections.

**Parameters:**
- `app_name`: Name of your DApp
- `app_url`: URL of your DApp
- `server_url`: Wallet server URL (default: http://localhost:8545)
- `permissions`: List of required permissions

**Methods:**
- `connect()`: Connect to wallet and request authorization
- `disconnect()`: Disconnect from wallet
- `get_wallet_info()`: Get wallet information
- `get_balance(contract)`: Get token balance
- `send_transaction(contract, function, kwargs)`: Send transaction
- `sign_message(message)`: Sign a message
- `add_token(contract_address, name, symbol)`: Add custom token

## Examples

See the `/examples` directory for complete examples:

- `simple_wallet.py`: Basic wallet implementation
- `simple_dapp.py`: Basic DApp connection
- `async_example.py`: Async/await usage
- `web_wallet.py`: Web-based wallet with UI

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=xian_uwp
```

### Contributing

Please ensure all changes maintain protocol compliance by running the test suite.

## License

MIT License - See LICENSE file for details.

## Support

- [Protocol Specification](../../protocol/SPECIFICATION.md)
- [GitHub Issues](https://github.com/xian-network/xian-uwp/issues)
- [Discord Community](https://discord.gg/xian)