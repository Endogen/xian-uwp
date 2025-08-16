# Xian Universal Wallet Protocol

## What Can Use Xian-UWP?

### 🔗 **Universal Compatibility Matrix**

| Component | Technology | Location | Examples |
|-----------|------------|----------|----------|
| **Wallets** | Python | Local or Server | Desktop GUI, CLI daemon, Web wallet, Server wallet |
| **DApps** | Any Language | Local or Server | React/Vue/Angular, Python/Flask, Node.js, Mobile apps, Desktop apps |

### 🌐 **Real-World Scenarios**

✅ **Local Python wallet** ↔ **Local Python DApp**  
✅ **Local Python wallet** ↔ **Server-hosted React DApp** (via CORS)  
✅ **Server Python wallet** ↔ **Any DApp anywhere** (via HTTP API)  
✅ **Local Python wallet** ↔ **Mobile app** (React Native, Flutter, native)  
✅ **Local Python wallet** ↔ **Desktop app** (Electron, Tauri, native)  

### 🔑 **Key Benefits**

- **Language Independent**: DApps can use any programming language that supports HTTP
- **Deployment Flexible**: Wallets and DApps can run locally or on servers
- **Technology Agnostic**: Works with any web framework, mobile framework, or desktop technology
- **Universal Interface**: Same API for all wallet types and DApp types

### ⚙️ **Technology Requirements**

| Component | Requirements | Notes |
|-----------|-------------|-------|
| **Wallets** | Python 3.11+ | Must implement the protocol server |
| **DApps** | HTTP client capability | Any language: Python, JavaScript, Go, Rust, Java, C#, etc. |
| **Communication** | HTTP/JSON | Standard web protocols, CORS-enabled |

## Overview

The Xian Universal Wallet Protocol provides a **unified HTTP API interface** that enables any DApp to communicate with any Xian wallet type through a standardized protocol. This eliminates the need for DApp developers to implement wallet-specific integrations and allows wallets to work with any DApp that supports the protocol.

**Core Principle**: Every wallet exposes the same HTTP API on `localhost:8545`, making wallet integration **programming language independent** and **wallet type agnostic**.

> **Important**: The default port `8545` was chosen to avoid conflicts with common development servers. If this port is already in use on your system, you can configure a different port when initializing the server.

## Quick Start

### For DApp Developers

```python
# 1. Install the protocol
pip install xian-uwp

# 2. Connect to any wallet
from xian_uwp.client import XianWalletClientSync

client = XianWalletClientSync("My DApp")
client.connect()

# 3. Use the wallet
info = client.get_wallet_info()
balance = client.get_balance("currency")
```

### For Wallet Developers

```python
# 1. Install the protocol
pip install xian-uwp

# 2. Create protocol server
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType

server = WalletProtocolServer(wallet_type=WalletType.DESKTOP)
server.wallet = your_wallet_instance
server.run()  # Starts on localhost:8545
```

## Universal Protocol Architecture

### 🏗️ **High-Level Architecture**

```
┌─────────────────────────────────┐    HTTP API    ┌─────────────────────────────────┐
│          Any DApp               │ ◄────────────► │         Any Wallet              │
│                                 │                │                                 │
│ • React/Vue/Angular (web)       │                │ • Desktop GUI (Python)         │
│ • Python/Flask/Django (server) │                │ • CLI daemon (Python)          │
│ • Node.js/Express (server)      │                │ • Web wallet (Python)          │
│ • Mobile (React Native/Flutter) │                │ • Server wallet (Python)       │
│ • Desktop (Electron/Tauri)      │                │                                 │
│ • Any language with HTTP        │                │ Exposes: localhost:8545        │
└─────────────────────────────────┘                └─────────────────────────────────┘
```

### 🔄 **Communication Flow**

```
DApp (Any Technology)  →  HTTP Request   →  Wallet (Python)
                      ←  JSON Response  ←
```

**Examples:**
- React DApp on Vercel → CORS-enabled HTTP → Local Python wallet
- Python Flask app → Direct HTTP → Server-hosted Python wallet  
- Mobile app → HTTP API → User's local Python wallet
- Electron desktop app → HTTP → Local Python wallet daemon

### 🎯 **Protocol Benefits**

- **Universal Interface**: All wallets expose identical HTTP API on port 8545
- **Language Independent**: DApps can use any programming language that supports HTTP
- **Deployment Flexible**: Both wallets and DApps can run locally or on servers
- **Technology Agnostic**: Works with any web framework, mobile framework, or desktop technology
- **CORS-Enabled**: Server-hosted DApps can connect to local wallets securely
- **Professional Features**: Session-based auth, permission system, caching, error handling

## How the Protocol Works

### 1. Standard Port & API
All Xian wallets run a local HTTP server on `localhost:8545` with standardized endpoints:

```
GET  /api/v1/wallet/status        # Check wallet availability
POST /api/v1/auth/request         # Request DApp authorization  
GET  /api/v1/wallet/info          # Get wallet information
GET  /api/v1/balance/{contract}   # Get token balance
POST /api/v1/transaction          # Send transaction
POST /api/v1/sign                 # Sign message
```

### 2. Authorization Flow
1. DApp requests authorization with permissions
2. Wallet shows approval UI to user
3. User approves/denies the request
4. Wallet returns session token to DApp
5. DApp uses token for subsequent requests

### 3. Session Management
- Time-limited session tokens (default 1 hour)
- Permission-based access control
- Auto-lock after inactivity
- Multiple concurrent sessions supported

## Wallet Implementation Guide

### Desktop Wallet Implementation

Desktop wallets run the protocol server directly in the application:

```python
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType

# Create server instance
server = WalletProtocolServer(wallet_type=WalletType.DESKTOP)

# Load your wallet
server.wallet = your_wallet_instance
server.password_hash = your_password_hash
server.is_locked = False

# Run server (same config for all wallet types)
server.run()  # Uses defaults: host="127.0.0.1", port=8545

# Or with custom port if 8545 is in use
server.run(port=8546)
```

**Key Implementation Points:**
- Embed server in your desktop app
- Handle user authorization via native UI
- Manage wallet unlock/lock states
- Optional: Add systray integration

### CLI Wallet Implementation  

CLI wallets run as daemon processes:

```bash
# Create wallet
xian-wallet create

# Start daemon
xian-wallet start --background

# Check status  
xian-wallet status
```

```python
# CLI daemon implementation
class CLIWalletDaemon:
    def start_daemon(self, password):
        # Load wallet from encrypted file
        wallet = self.load_wallet(password)
        
        # Create and start server (same config for all wallet types)
        server = WalletProtocolServer(wallet_type=WalletType.CLI)
        server.wallet = wallet
        server.run()  # Uses defaults: host="127.0.0.1", port=8545
```

**Key Implementation Points:**
- Encrypted wallet storage on disk
- Background daemon process
- Command-line interface for management
- Auto-approval or terminal-based approval UI

### Web Wallet (Flet-based) Implementation

Web wallets run in the browser but use Python/Flet:

```python
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType
import flet as ft

# Create server instance  
server = WalletProtocolServer(wallet_type=WalletType.WEB)

# Load your wallet
server.wallet = your_wallet_instance
server.password_hash = your_password_hash
server.is_locked = False

# Run server in background thread (same config for all wallet types)
def run_server():
    server.run()  # Uses defaults: host="127.0.0.1", port=8545

# Run Flet web interface on different port
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)
```

**Key Implementation Points:**
- Flet-based web interface (100% Python)
- Same codebase as desktop wallet
- Works on any device with browser
- No browser extension needed
- Professional UI with tabs and responsive design

## DApp Integration

### Using the Universal Client

DApps use the same client library regardless of wallet type:

```python
from xian_uwp.client import XianWalletClientSync

# Create client - works with any wallet type
client = XianWalletClientSync(
    app_name="My DApp", 
    app_url="http://localhost:8080",
    server_url="http://localhost:8545"  # Optional: custom port
)

# Connect to any wallet
if client.connect():
    # Use identical API regardless of wallet type
    wallet_info = client.get_wallet_info()
    balance = client.get_balance("currency")
    result = client.send_transaction("currency", "transfer", {"to": "addr", "amount": 100})
else:
    print("Failed to connect to wallet")
```

### Legacy Compatibility

For existing JavaScript DApps:

```javascript
// Same API as original dapp-utils
XianWalletUtils.init();
const info = await XianWalletUtils.requestWalletInfo();
const balance = await XianWalletUtils.getBalance("currency");
```

## API Reference

### Core Endpoints

#### GET /api/v1/wallet/status
Check if wallet is available and its current state. No authentication required.

**Response:**
```json
{
  "available": true,
  "locked": false,
  "wallet_type": "desktop",
  "network": "https://testnet.xian.org",
  "chain_id": "xian-testnet",
  "version": "1.0.0"
}
```

#### POST /api/v1/auth/request
Request authorization from the wallet. The wallet will prompt the user to approve/deny.

**Request Body:**
```json
{
  "app_name": "My DApp",
  "app_url": "http://localhost:8080", 
  "permissions": ["wallet_info", "balance", "transactions"],
  "description": "Optional description of why permissions are needed"
}
```

**Available Permissions:**
- `wallet_info` - Read wallet address and basic info
- `balance` - Read token balances
- `transactions` - Send transactions
- `sign_message` - Sign messages
- `add_token` - Add custom tokens to wallet

**Response:**
```json
{
  "request_id": "req_abc123",
  "status": "pending"
}
```

#### POST /api/v1/auth/approve/{request_id}
Approve an authorization request. Usually called by the wallet UI after user approval.

**Response:**
```json
{
  "session_token": "token_xyz789",
  "expires_at": "2024-01-01T12:00:00Z",
  "permissions": ["wallet_info", "balance", "transactions"]
}
```

#### POST /api/v1/auth/deny/{request_id}
Deny an authorization request. Usually called by the wallet UI after user denial.

**Response:**
```json
{
  "status": "denied",
  "reason": "User denied authorization"
}
```

#### GET /api/v1/wallet/info
*Requires Authorization: Bearer {session_token}*

Get wallet information. Requires `wallet_info` permission.

**Response:**
```json
{
  "address": "abc123...",
  "truncated_address": "abc123...xyz789",
  "locked": false,
  "chain_id": "xian-testnet", 
  "network": "https://testnet.xian.org",
  "wallet_type": "desktop",
  "version": "1.0.0"
}
```

#### POST /api/v1/wallet/unlock
Unlock the wallet with password. No authentication required.

**Request Body:**
```json
{
  "password": "wallet_password"
}
```

**Response:**
```json
{
  "unlocked": true,
  "message": "Wallet unlocked successfully"
}
```

#### POST /api/v1/wallet/lock
Lock the wallet. Requires valid session.

**Response:**
```json
{
  "locked": true,
  "message": "Wallet locked successfully"
}
```

#### GET /api/v1/balance/{contract}
*Requires Authorization: Bearer {session_token}*

```json
{
  "balance": 1000.0,
  "contract": "currency",
  "symbol": "XIAN",
  "decimals": 8
}
```

#### POST /api/v1/transaction
*Requires Authorization: Bearer {session_token}*

Send a transaction to the blockchain. Requires `transactions` permission.

**Request Body:**
```json
{
  "contract": "currency",
  "function": "transfer",
  "kwargs": {"to": "recipient_address", "amount": 100},
  "stamps_supplied": 50000
}
```

**Response (Success):**
```json
{
  "success": true,
  "transaction_hash": "tx_hash_here",
  "result": "transaction_result",
  "gas_used": 45000
}
```

**Response (Failure):**
```json
{
  "success": false,
  "errors": ["Insufficient balance"],
  "transaction_hash": null
}
```

#### POST /api/v1/sign
*Requires Authorization: Bearer {session_token}*

Sign a message with the wallet's private key. Requires `sign_message` permission.

**Request Body:**
```json
{
  "message": "Message to sign"
}
```

**Response:**
```json
{
  "message": "Message to sign",
  "signature": "signature_hex",
  "signer": "wallet_address"
}
```

#### POST /api/v1/tokens/add
*Requires Authorization: Bearer {session_token}*

Add a custom token to the wallet. Requires `add_token` permission.

**Request Body:**
```json
{
  "contract_address": "token_contract",
  "token_name": "My Token",
  "token_symbol": "MTK"
}
```

**Response:**
```json
{
  "accepted": true,
  "contract": "token_contract"
}
```

### WebSocket API

#### WS /ws/v1
WebSocket endpoint for real-time communication. Useful for wallet UIs and monitoring.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8545/ws/v1');
```

**Message Types:**

**Ping/Pong:**
```json
// Send
{"type": "ping"}

// Receive
{"type": "pong", "timestamp": "2024-01-01T12:00:00Z"}
```

**Authorization Request Event:**
```json
{
  "type": "authorization_request",
  "request": {
    "request_id": "req_abc123",
    "app_name": "My DApp",
    "permissions": ["wallet_info", "balance"],
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

**Transaction Event:**
```json
{
  "type": "transaction",
  "data": {
    "hash": "tx_hash",
    "status": "pending|success|failed",
    "contract": "currency",
    "function": "transfer"
  }
}
```

## Installation & Setup

### 1. Install Core Protocol

```bash
pip install xian-uwp
```

**This installs all core dependencies:**
- `fastapi` - HTTP API server framework
- `uvicorn` - ASGI server to run FastAPI
- `httpx` - Async HTTP client for wallet connections  
- `websockets` - WebSocket support for real-time communication
- `pydantic` - Data validation and serialization
- `xian-py` - Xian blockchain SDK for wallet operations

> **Note**: The PyPI package contains only the core protocol. To run the example wallets and DApps, you need to clone this repository and run them from source.

### 2. Optional Dependencies (Install as needed)

**For Desktop Wallet Development:**
```bash
pip install flet>=0.28.3
```

**For CLI Wallet Development:**
```bash
pip install click>=8.2.1
pip install cryptography>=41.0.0  # For encrypted wallet storage
```

**For Running Examples:**
```bash
pip install flet>=0.28.3  # Required for Flet examples
pip install reflex>=0.8.6  # Required for Reflex examples
```

### 2. Using in Your Own Projects

After installing `pip install xian-uwp`, you can use the protocol in your own wallet or DApp:

**For DApp Development:**
```python
from xian_uwp.client import XianWalletClientSync

# Connect to any wallet
client = XianWalletClientSync("My DApp")
client.connect()

# Use wallet functionality
info = client.get_wallet_info()
balance = client.get_balance("currency")
```

**For Wallet Development:**
```python
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType

# Create protocol server
server = WalletProtocolServer(wallet_type=WalletType.DESKTOP)
server.wallet = your_wallet_instance
server.run()  # Starts on localhost:8545
```

### 3. Project Structure

```
xian-universal-wallet-protocol/
├── xian_uwp/
│   ├── __init__.py
│   ├── models.py          # Data models & constants
│   ├── server.py          # Universal protocol server  
│   └── client.py          # Universal client library
├── examples/
│   ├── wallets/           # Wallet implementation examples
│   │   ├── desktop.py     # Desktop wallet example (requires: flet)
│   │   ├── web.py         # Web wallet example (requires: flet)
│   │   └── cli.py         # CLI wallet example (requires: click, cryptography)
│   └── dapps/             # DApp examples
│       ├── universal_dapp.py  # Flet DApp example (requires: flet)
│       ├── reflex_dapp.py     # Reflex DApp example (requires: reflex)
│       └── html-js-dapp/      # Pure HTML/JS DApp example (no dependencies)
├── tests/                 # Test suite
│   ├── test_simple.py     # Basic component tests
│   ├── test_protocol.py   # Protocol integration tests
│   ├── test_server.py     # Server functionality tests
│   └── test_e2e.py        # End-to-end tests
└── README.md
```

**Important Notes:**
- **Core Protocol**: Only files in `xian_uwp/` directory are the actual protocol implementation
- **Examples**: All files in `examples/` are reference implementations to learn from
- **PyPI Package**: Install with `pip install xian-uwp` for production use
- **Development**: When running examples from source, use `PYTHONPATH=.` to import the protocol modules correctly

**Example Files Explained:**
- `desktop.py` - Shows how to embed the protocol server in a desktop GUI application
- `web.py` - Demonstrates a browser-based wallet using Flet (100% Python, no JavaScript)
- `cli.py` - Example of a command-line wallet with daemon mode
- `universal_dapp.py` - Sample DApp showing wallet integration with Flet UI
- `reflex_dapp.py` - Sample DApp using the Reflex framework instead of Flet
- `html-js-dapp/` - Pure HTML/JavaScript DApp example (no Python frameworks required)

### 4. Run Desktop Wallet Example

```bash
# Install dependencies
pip install xian-uwp flet>=0.28.3

# Run desktop wallet example (requires source code)
PYTHONPATH=. python examples/wallets/desktop.py
```

### 5. Run Web Wallet Example

```bash
# Install dependencies
pip install xian-uwp flet>=0.28.3

# Run web wallet example (opens in browser, requires source code)
PYTHONPATH=. python examples/wallets/web.py
```

### 6. Run CLI Wallet Example

```bash
# Install dependencies
pip install xian-uwp click>=8.2.1 cryptography>=41.0.0

# Create wallet (requires source code)
PYTHONPATH=. python examples/wallets/cli.py create

# Start daemon
PYTHONPATH=. python examples/wallets/cli.py start
```

### 7. Run DApp Examples

**Flet DApp Example:**
```bash
# Install dependencies
pip install xian-uwp flet>=0.28.3

# Run Flet DApp example (requires source code)
PYTHONPATH=. python examples/dapps/universal_dapp.py
```

**Reflex DApp Example:**
```bash
# Install dependencies
pip install xian-uwp reflex>=0.8.6

# Run Reflex DApp example (requires source code)
cd examples/dapps && PYTHONPATH=../.. reflex run
```

**HTML/JavaScript DApp Example:**
```bash
# No dependencies required - pure HTML/CSS/JavaScript

# Serve the files (required for CORS)
cd examples/dapps/html-js-dapp
python -m http.server 8080

# Open http://localhost:8080 in your browser
```

## Example Implementations

### Flet DApp Example

```python
# examples/dapps/universal_dapp.py
# Requires: pip install flet>=0.28.3

from xian_uwp.client import XianWalletClientSync

class MyDApp:
    def __init__(self):
        self.client = XianWalletClientSync("My DApp")
    
    def connect_wallet(self):
        self.client.connect()
        info = self.client.get_wallet_info()
        print(f"Connected: {info.address}")
    
    def send_tokens(self, to, amount):
        result = self.client.send_transaction(
            "currency", "transfer", 
            {"to": to, "amount": amount}
        )
        return result.success
```

### Reflex DApp Example

```python
# examples/dapps/reflex_dapp.py  
# Requires: pip install reflex>=0.8.6

import reflex as rx
from xian_uwp.client import XianWalletClientSync

class WalletState(rx.State):
    """Wallet DApp state with Reflex"""
    is_connected: bool = False
    wallet_address: str = "No wallet connected"
    
    async def connect_wallet(self):
        self._client = XianWalletClientSync("Reflex DApp")
        success = self._client.connect()
        if success:
            info = self._client.get_wallet_info()
            self.is_connected = True
            self.wallet_address = info.truncated_address

def index():
    return rx.center(
        rx.vstack(
            rx.heading("Universal Xian DApp"),
            rx.text(WalletState.wallet_address),
            rx.button(
                "Connect Wallet",
                on_click=WalletState.connect_wallet,
                disabled=WalletState.is_connected
            )
        )
    )

app = rx.App()
app.add_page(index)
```

**All examples work with any wallet type:** Desktop, Web, CLI, or Hardware wallets.

### HTML/JavaScript DApp Example

```javascript
// examples/dapps/html-js-dapp/xian-wallet-client.js
// Pure JavaScript client - no frameworks required

class XianWalletClient {
    constructor(appName, appUrl = 'http://localhost', serverUrl = 'http://127.0.0.1:8545') {
        this.appName = appName;
        this.appUrl = appUrl;
        this.serverUrl = serverUrl;
        this.sessionToken = null;
        this.isConnected = false;
    }

    async connect() {
        // Request authorization
        const authResponse = await this.requestAuthorization();
        
        // Wait for user approval
        const approval = await this.pollForApproval(authResponse.request_id);
        
        this.sessionToken = approval.session_token;
        this.isConnected = true;
        
        return { success: true, walletInfo: await this.getWalletInfo() };
    }

    async sendTransaction(contract, functionName, kwargs, stampsSupplied = 50000) {
        const response = await fetch(`${this.serverUrl}/api/v1/transaction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.sessionToken}`
            },
            body: JSON.stringify({
                contract, function: functionName, kwargs, stamps_supplied: stampsSupplied
            })
        });
        return await response.json();
    }
}

// Usage in HTML
const client = new XianWalletClient('My HTML DApp');
await client.connect();
const balance = await client.getBalance('currency');
```

**Features:**
- **Pure HTML/CSS/JavaScript** - No build tools or frameworks
- **Universal Wallet Support** - Works with any wallet type
- **Complete API Coverage** - All protocol features available
- **Modern JavaScript** - Uses async/await and fetch API

### Legacy Web DApp Example

```html
<!-- For legacy JavaScript compatibility -->
<script>
// Works with any wallet type (desktop, web, CLI)
XianWalletUtils.init().then(() => {
    return XianWalletUtils.requestWalletInfo();
}).then(info => {
    console.log('Connected:', info.address);
});
</script>
```

**Note:** All wallet types provide the same localhost:8545 API, so existing JavaScript code works unchanged.

## Configuration Options

### Server Configuration

```python
from xian_uwp.server import WalletProtocolServer
from xian_uwp.models import WalletType

# Create server with options
server = WalletProtocolServer(
    wallet_type=WalletType.DESKTOP,
    session_duration=7200,  # 2 hours (default: 3600)
    auto_lock_minutes=15,   # Auto-lock after 15 min (default: 30)
    max_sessions=10         # Max concurrent sessions (default: 100)
)

# Custom network configuration
server.network_url = "https://mainnet.xian.org"
server.chain_id = "xian-mainnet"

# Run on custom port
server.run(host="127.0.0.1", port=8546)
```

### Client Configuration

```python
from xian_uwp.client import XianWalletClientSync

# Create client with options
client = XianWalletClientSync(
    app_name="My DApp",
    app_url="http://localhost:3000",
    server_url="http://localhost:8546",  # Custom wallet URL/port
    permissions=["wallet_info", "balance", "transactions"]  # Request specific permissions
)

# Async client with custom settings
from xian_uwp.client import XianWalletClient

async_client = XianWalletClient(
    app_name="My Async DApp",
    app_url="http://localhost:3000",
    server_url="http://localhost:8545",
    permissions=["wallet_info", "balance"]
)
```

### CORS Configuration

For web-based DApps hosted on servers, the protocol includes comprehensive CORS support:

```python
from xian_uwp import create_server, CORSConfig

# Development mode (default) - allows common dev ports
server = create_server(cors_config=CORSConfig.localhost_dev())
server.run()

# Production mode - specific origins only
cors_config = CORSConfig.production([
    "https://mydapp.com",
    "https://app.mydapp.com"
])
server = create_server(cors_config=cors_config)
server.run(host="0.0.0.0", port=8545)  # Allow external connections

# Custom CORS configuration
cors_config = CORSConfig(
    allow_origins=["http://localhost:3000", "https://mydapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)
server = create_server(cors_config=cors_config)
```

#### CORS Presets

- **`CORSConfig.development()`**: Allows all origins (for development)
- **`CORSConfig.localhost_dev()`**: Common dev ports (3000, 5173, 8080, etc.)
- **`CORSConfig.production(origins)`**: Specific origins only (for production)

#### Web DApp Integration

```javascript
// JavaScript client connecting to local wallet
const client = new XianWalletClient(
    'My Web DApp',
    window.location.origin,  // Current web app origin
    'http://localhost:8545'  // Local wallet server
);

await client.connect();
const balance = await client.getBalance('currency');
```

## Security Considerations

### Local-Only Communication
- Server binds to 127.0.0.1 only (no external access)
- No cross-origin issues (same machine)
- No network exposure of wallet operations

### Session Security
- Time-limited tokens with automatic expiration
- Permission-based access control
- Session invalidation on wallet lock
- Multiple session support with individual revocation

### Data Protection
- No sensitive data in logs
- Encrypted wallet storage (CLI)
- Secure password handling (SHA256 minimum)
- Auto-lock on inactivity

## Production Deployment

### For Wallet Developers

1. **Implement the protocol server** in your wallet
2. **Handle authorization UI** for user approval
3. **Manage session lifecycle** properly
4. **Add proper error handling** and logging
5. **Test with multiple DApps** to ensure compatibility

### For DApp Developers

1. **Use the universal client library** for any language
2. **Handle connection errors** gracefully
3. **Implement user-friendly authorization** requests
4. **Cache wallet info** appropriately
5. **Test with multiple wallet types**

## Migration from dapp-utils

### For Existing DApps

**No changes required!** The protocol provides full backward compatibility:

```javascript
// Existing code works unchanged
XianWalletUtils.init();
const balance = await XianWalletUtils.getBalance("currency");
```

### Benefits of Migration

- **Multi-wallet support**: Works with desktop, CLI, and web wallets
- **Better performance**: Local HTTP is faster than extension messaging
- **More reliable**: Direct communication, no extension dependencies
- **Language agnostic**: Use Python, JavaScript, or any language

## Development & Testing

### Running Tests

```bash
# Install test dependencies first
poetry install --with test

# Run all tests with coverage
poetry run pytest

# Run without coverage (if pytest-cov not installed)
poetry run pytest --no-cov

# Run specific test categories
poetry run pytest -m unit      # Unit tests only
poetry run pytest -m cors      # CORS tests only
poetry run pytest -m e2e       # End-to-end tests only
```

**Common Issue**: If you get `unrecognized arguments: --cov=xian_uwp`, install test dependencies:
```bash
poetry install --with test
# Or: pip install pytest pytest-cov pytest-asyncio pytest-mock
```

See `tests/README.md` for detailed testing documentation.

### Running the Protocol Server Directly

```bash
# Start a demo server for testing
python -m protocol.server

# The server will:
# - Start on localhost:8545
# - Create a demo wallet automatically
# - Log the wallet address for testing
# - Accept connections from DApps
```

### Testing with the Client

```python
from xian_uwp.client import XianWalletClientSync

# Create client
client = XianWalletClientSync("Test App")

# Connect and request authorization
if client.connect():
    print("Connected!")
    
    # The wallet UI will show authorization request
    # After approval, you can use the wallet
    info = client.get_wallet_info()
    print(f"Wallet: {info.truncated_address}")
```

### Testing Authorization Flow

```python
import asyncio
from xian_uwp.client import XianWalletClient

async def test_auth_flow():
    client = XianWalletClient("Test DApp")
    
    # Request authorization
    request_id = await client._request_authorization(["wallet_info", "balance"])
    print(f"Authorization requested: {request_id}")
    
    # In a real wallet, user would approve via UI
    # For testing, you can manually approve:
    # POST http://localhost:8545/api/v1/auth/approve/{request_id}
    
    # Wait for approval
    session = await client._wait_for_approval(request_id)
    if session:
        print(f"Approved! Token: {session.session_token}")

asyncio.run(test_auth_flow())
```

### Test Different Wallet Types

```bash
# Test desktop wallet example
PYTHONPATH=. python examples/wallets/desktop.py

# Test web wallet example
PYTHONPATH=. python examples/wallets/web.py

# Test CLI wallet example
PYTHONPATH=. python examples/wallets/cli.py start
```

### Run Examples

```bash
# Install example dependencies first
pip install flet>=0.28.3      # For Flet examples
pip install reflex>=0.8.6     # For Reflex examples

# Run Flet DApp example
PYTHONPATH=. python examples/dapps/universal_dapp.py

# Run Reflex DApp example
cd examples/dapps && PYTHONPATH=../.. reflex run

# Run HTML/JS DApp example (no dependencies)
cd examples/dapps/html-js-dapp && python -m http.server 8080
# Then open http://localhost:8080 in your browser
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (invalid endpoint or resource)
- `423` - Locked (wallet is locked)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "detail": "Human-readable error message"
}
```

### Common Error Scenarios

**Wallet Locked:**
```json
{
  "detail": "Wallet is locked"
}
```
*Solution: Unlock wallet via `/api/v1/wallet/unlock`*

**Invalid Session:**
```json
{
  "detail": "Invalid or expired session"
}
```
*Solution: Request new authorization*

**Insufficient Permissions:**
```json
{
  "detail": "Insufficient permissions"
}
```
*Solution: Request authorization with required permissions*

## Troubleshooting

### Common Issues

**Connection Refused**
- Ensure wallet server is running on port 8545
- Check if another service is using port 8545
- Try a different port: `server.run(port=8546)`
- Check firewall settings

**Authorization Failed**
- Verify wallet is unlocked
- Check authorization request was approved
- Ensure permissions match what DApp requests

**Session Expired**
- Tokens expire after 1 hour by default
- Client will auto-reconnect
- Can configure longer expiry in server

### Debug Mode

```bash
# Enable debug logging
export XIAN_WALLET_DEBUG=1
PYTHONPATH=. python examples/wallets/desktop.py

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### For Wallet Developers

1. **Authorization UI**
   - Show clear permission requests
   - Display app name and URL prominently
   - Allow users to approve/deny individual permissions
   - Show session duration

2. **Security**
   - Always validate session tokens
   - Consider implementing rate limiting
   - Log authorization attempts
   - Auto-lock on inactivity (configurable)
   - Clear sessions on wallet lock

3. **User Experience**
   - Show pending authorization requests
   - Notify users of transaction requests
   - Display clear error messages
   - Implement transaction confirmation UI

### For DApp Developers

1. **Connection Handling**
   ```python
   # Always check connection status
   if not client.is_connected():
       client.connect()
   
   # Handle connection failures gracefully
   try:
       balance = client.get_balance("currency")
   except ConnectionError:
       # Show user-friendly error
       pass
   ```

2. **Permission Management**
   - Only request necessary permissions
   - Explain why permissions are needed
   - Handle permission denials gracefully
   - Cache wallet info appropriately

3. **Error Handling**
   - Catch and handle all exceptions
   - Show meaningful error messages
   - Implement retry logic for transient failures
   - Log errors for debugging

## Future Enhancements

- **Hardware wallet support** via protocol adapters
- **Multi-network support** (mainnet, testnet, custom)
- **Enhanced security** with HSM integration
- **Browser extension version** of web wallet (optional)
- **Mobile wallet support** via Flet mobile apps
- **Cross-platform notifications** for transaction requests
- **QR code authorization** for mobile/remote wallets
- **Multi-signature support** for shared wallets

---

**The Universal Wallet Protocol makes Xian wallet integration simple, secure, and unified across all platforms.**