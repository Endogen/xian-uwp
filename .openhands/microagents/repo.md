# Xian Universal Wallet Protocol (UWP)

## Purpose
The Xian Universal Wallet Protocol provides a **unified HTTP API interface** that enables any DApp to communicate with any Xian wallet type (desktop, web, CLI) through a standardized protocol. This eliminates the need for DApp developers to implement wallet-specific integrations and allows wallets to work with any DApp that supports the protocol.

Key benefits:
- **Universal Interface**: All wallets expose identical HTTP API on `localhost:8545`
- **Language Independent**: Works with any programming language that can make HTTP requests
- **Wallet Agnostic**: DApps work seamlessly with desktop, web, or CLI wallets
- **Drop-in Replacement**: Compatible with existing dapp-utils API patterns
- **Professional Features**: Session-based auth, permission system, caching, error handling

## General Setup

### Core Dependencies
- **Python 3.11+** with Poetry or pip
- **Core packages**: `fastapi`, `uvicorn`, `httpx`, `websockets`, `pydantic`, `xian-py`
- **Optional packages**: `flet` (desktop/web wallets), `reflex` (web DApps), `click` (CLI), `cryptography` (encryption)

### Installation
```bash
# Core protocol
pip install fastapi uvicorn httpx websockets pydantic xian-py

# Example dependencies (as needed)
pip install flet>=0.28.3 reflex>=0.8.6 click>=8.2.1 cryptography>=41.0.0
```

### Running Examples
All examples require `PYTHONPATH=.` to import protocol modules:
```bash
PYTHONPATH=. python examples/wallets/cli.py create
PYTHONPATH=. python examples/dapps/universal_dapp.py
```

## Repository Structure

### Core Protocol (`/protocol/`)
- **`models.py`**: Pydantic data models, enums (WalletType, Permission, etc.), request/response schemas
- **`server.py`**: FastAPI-based HTTP server that wallets implement to expose the universal API
- **`client.py`**: Client library for DApps to connect to any wallet (sync/async versions)
- **`__init__.py`**: Package initialization

### Example Implementations (`/examples/`)

#### Wallets (`/examples/wallets/`)
- **`cli.py`**: Command-line wallet with encrypted storage, daemon mode, Click-based interface
- **`desktop.py`**: Desktop GUI wallet using Flet framework
- **`web.py`**: Web-based wallet using Flet web mode

#### DApps (`/examples/dapps/`)
- **`universal_dapp.py`**: Universal DApp demo using Flet that works with any wallet
- **`reflex_dapp.py`**: Web DApp using Reflex framework
- **`rxconfig.py`**: Reflex configuration file

### Configuration & Documentation
- **`pyproject.toml`**: Poetry project configuration with core dependencies
- **`requirements.txt`**: Pip requirements file
- **`README.md`**: Complete documentation with architecture, API reference, examples
- **`QUICK_REFERENCE.md`**: Developer cheat sheet with essential commands and patterns

### Testing & Verification
- **`test_*.py`**: Test files for protocol components, server functionality, and end-to-end scenarios
- **`TESTING_SUMMARY.md`**: Comprehensive testing documentation
- **`VERIFICATION_REPORT.md`**: Test results and verification status

### Protocol Architecture
```
┌─────────────────┐    HTTP API      ┌─────────────────┐
│   Any DApp      │ ◄──────────────► │  Any Wallet     │
│ (Python, JS,    │  localhost:8545  │ (Desktop, Web,  │
│  etc.)          │                  │  CLI)           │
└─────────────────┘                  └─────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│ Universal       │                  │ Protocol Server │
│ Client Library  │                  │ (Port 8545)     │
└─────────────────┘                  └─────────────────┘
```

The protocol uses standard HTTP endpoints (`/api/v1/wallet/status`, `/api/v1/auth/request`, etc.) with session-based authentication and permission management.