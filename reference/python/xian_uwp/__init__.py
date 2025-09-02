"""
Xian Universal Wallet Protocol - Python Reference Implementation
Language-agnostic protocol for wallet and DApp communication on Xian blockchain
"""

__version__ = "2.0.0"
__author__ = "Xian Network"
__description__ = "Python reference implementation of the Xian Universal Wallet Protocol"
__protocol_version__ = "2.0.0"

# Core imports for easy access
from .models import (
    # Enums
    WalletType,
    ConnectionStatus,
    Permission,
    
    # Data models
    WalletInfo,
    BalanceResponse,
    TransactionResult,
    SignatureResponse,
    AuthorizationResponse,
    
    # Request models
    AuthorizationRequest,
    TransactionRequest,
    SignMessageRequest,
    AddTokenRequest,
    
    # Configuration
    ProtocolConfig,
    Endpoints,
    ErrorCodes,
    CORSConfig
)

from .server import WalletProtocolServer

from .client import (
    XianWalletClient,
    XianWalletClientSync,
    WalletProtocolError,
    create_client
)

# Convenience functions
def create_server(
    wallet_type: WalletType = WalletType.DESKTOP,
    cors_config: CORSConfig = None
) -> WalletProtocolServer:
    """Create a wallet protocol server instance"""
    return WalletProtocolServer(wallet_type=wallet_type, cors_config=cors_config)

def create_dapp_client(
    app_name: str,
    app_url: str = "http://localhost",
    async_mode: bool = False
):
    """Create a DApp client for connecting to wallets"""
    return create_client(app_name, app_url, async_mode=async_mode)



# Protocol information
PROTOCOL_INFO = {
    "version": __version__,
    "default_port": ProtocolConfig.DEFAULT_PORT,
    "default_host": ProtocolConfig.DEFAULT_HOST,
    "api_version": ProtocolConfig.API_VERSION,
    "supported_wallet_types": [wt.value for wt in WalletType],
    "available_permissions": [p.value for p in Permission]
}

def get_protocol_info():
    """Get protocol information"""
    return PROTOCOL_INFO.copy()

# Health check function
async def check_wallet_available(
    host: str = ProtocolConfig.DEFAULT_HOST,
    port: int = ProtocolConfig.DEFAULT_PORT
) -> bool:
    """Check if a wallet is available on the specified host/port"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{host}:{port}{Endpoints.WALLET_STATUS}")
            if response.status_code == 200:
                data = response.json()
                return data.get("available", False)
            return False
    except:
        return False

def check_wallet_available_sync(
    host: str = ProtocolConfig.DEFAULT_HOST,
    port: int = ProtocolConfig.DEFAULT_PORT
) -> bool:
    """Synchronous version of wallet availability check"""
    import asyncio
    return asyncio.run(check_wallet_available(host, port))

# Export all important classes and functions
__all__ = [
    # Core classes
    "WalletProtocolServer",
    "XianWalletClient", 
    "XianWalletClientSync",
    "WalletProtocolError",
    
    # Enums
    "WalletType",
    "ConnectionStatus", 
    "Permission",
    
    # Data models
    "WalletInfo",
    "BalanceResponse",
    "TransactionResult",
    "SignatureResponse",
    "AuthorizationResponse",
    
    # Request models
    "AuthorizationRequest",
    "TransactionRequest", 
    "SignMessageRequest",
    "AddTokenRequest",
    
    # Configuration
    "ProtocolConfig",
    "Endpoints",
    "ErrorCodes",
    "CORSConfig",
    
    # Factory functions
    "create_server",
    "create_dapp_client",
    "create_client",
    
    # Utility functions
    "get_protocol_info",
    "check_wallet_available",
    "check_wallet_available_sync",
    
    # Version info
    "__version__",
    "PROTOCOL_INFO"
]

