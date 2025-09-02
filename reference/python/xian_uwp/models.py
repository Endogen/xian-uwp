"""
Xian Wallet Protocol - Data Models
Universal data models for all wallet implementations
"""

import re

from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class WalletType(str, Enum):
    """Supported wallet types"""
    DESKTOP = "desktop"
    WEB = "web" 
    CLI = "cli"
    HARDWARE = "hardware"
    MOBILE = "mobile"


class ConnectionStatus(str, Enum):
    """Connection status states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    LOCKED = "locked"


class Permission(str, Enum):
    """Available permissions for DApps"""
    WALLET_INFO = "wallet_info"
    BALANCE = "balance"
    TRANSACTIONS = "transactions"
    SIGN_MESSAGE = "sign_message"
    ADD_TOKEN = "add_token"


class AuthStatus(str, Enum):
    """Authorization status states"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


# Request Models
class AuthorizationRequest(BaseModel):
    """Authorization request from DApp"""
    app_name: str = Field(..., min_length=1, max_length=100)
    app_url: str = Field(..., min_length=1, max_length=500)
    permissions: List[Permission]
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator('app_url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        return v
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions_not_empty(cls, v):
        """Ensure permissions list is not empty and deduplicate"""
        if not v:
            raise ValueError('At least one permission is required')
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for perm in v:
            if perm not in seen:
                seen.add(perm)
                deduped.append(perm)
        return deduped


class TransactionRequest(BaseModel):
    """Transaction request"""
    contract: str = Field(..., min_length=1, max_length=100)
    function: str = Field(..., min_length=1, max_length=100)
    kwargs: Dict[str, Any]
    stamps_supplied: Optional[int] = Field(None, ge=0)


class SignMessageRequest(BaseModel):
    """Message signing request"""
    message: str = Field(..., min_length=1, max_length=10000)


class AddTokenRequest(BaseModel):
    """Add token request"""
    contract_address: str = Field(..., min_length=1, max_length=100)
    token_name: Optional[str] = Field(None, max_length=100)
    token_symbol: Optional[str] = Field(None, max_length=20)
    decimals: Optional[int] = Field(None, ge=0, le=18)


class UnlockRequest(BaseModel):
    """Wallet unlock request"""
    password: str = Field(..., min_length=1)


# Response Models
class WalletInfo(BaseModel):
    """Wallet information response"""
    address: str
    truncated_address: str
    locked: bool
    chain_id: Optional[str] = None
    network: Optional[str] = None
    wallet_type: WalletType
    version: str = "1.0.0"


class BalanceResponse(BaseModel):
    """Balance query response"""
    balance: Union[float, int]
    contract: str
    symbol: Optional[str] = None
    decimals: Optional[int] = None


class TransactionResult(BaseModel):
    """Transaction result"""
    success: bool
    transaction_hash: Optional[str] = None
    result: Optional[Any] = None
    errors: Optional[List[str]] = None
    gas_used: Optional[int] = None


class SignatureResponse(BaseModel):
    """Message signature response"""
    signature: str
    message: str
    address: str


class AuthorizationResponse(BaseModel):
    """Authorization response"""
    session_token: str
    expires_at: datetime
    permissions: List[Permission]
    status: str = "approved"
    
    @field_serializer('expires_at')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    code: str
    details: Optional[str] = None


class StatusResponse(BaseModel):
    """Wallet status response"""
    available: bool
    locked: bool
    wallet_type: WalletType
    network: Optional[str] = None
    chain_id: Optional[str] = None
    version: str


# Internal Models
class Session(BaseModel):
    """Internal session model"""
    token: str
    app_name: str
    app_url: str
    permissions: List[Permission]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    request_id: Optional[str] = None
    
    @field_serializer('created_at', 'expires_at', 'last_activity')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class PendingRequest(BaseModel):
    """Pending authorization request"""
    request_id: str
    app_name: str
    app_url: str
    permissions: List[Permission]
    description: Optional[str]
    created_at: datetime
    status: str = "pending"
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


# CORS Configuration
class CORSConfig(BaseModel):
    """CORS configuration for web-based DApps"""
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: List[str] = Field(default_factory=lambda: ["*"])
    allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    expose_headers: List[str] = Field(default_factory=list)
    max_age: int = 600
    
    @classmethod
    def development(cls) -> "CORSConfig":
        """Development CORS configuration - allows all origins"""
        return cls(
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600
        )
    
    @classmethod
    def production(cls, allowed_origins: List[str]) -> "CORSConfig":
        """Production CORS configuration - specific origins only"""
        return cls(
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With"
            ],
            expose_headers=["Content-Length", "Content-Type"],
            max_age=86400  # 24 hours
        )
    
    @classmethod
    def localhost_dev(cls, ports: List[int] = None) -> "CORSConfig":
        """Localhost development configuration for common dev server ports"""
        if ports is None:
            ports = [3000, 3001, 5000, 5173, 8000, 8080, 8081, 51644, 57158]
        
        origins = [f"http://localhost:{port}" for port in ports]
        origins.extend([f"http://127.0.0.1:{port}" for port in ports])
        origins.extend(["http://localhost", "http://127.0.0.1"])
        
        return cls(
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600
        )


# Protocol Constants
class ProtocolConfig:
    """Protocol configuration constants"""
    DEFAULT_PORT = 8545
    DEFAULT_HOST = "localhost"
    API_VERSION = "v1"
    PROTOCOL_VERSION = "2.0.0"
    SESSION_TIMEOUT_MINUTES = 60
    AUTO_LOCK_MINUTES = 30
    MAX_SESSIONS = 10
    CACHE_TTL_SECONDS = 30


# API Endpoints
class Endpoints:
    """API endpoint constants"""
    # Auth endpoints
    AUTH_REQUEST = "/api/v1/auth/request"
    AUTH_STATUS = "/api/v1/auth/status/{request_id}"
    AUTH_PENDING = "/api/v1/auth/pending"
    AUTH_APPROVE = "/api/v1/auth/approve/{request_id}"
    AUTH_DENY = "/api/v1/auth/deny/{request_id}"
    AUTH_REVOKE = "/api/v1/auth/revoke"
    
    # Wallet endpoints
    WALLET_STATUS = "/api/v1/wallet/status"
    WALLET_INFO = "/api/v1/wallet/info"
    WALLET_UNLOCK = "/api/v1/wallet/unlock"
    WALLET_LOCK = "/api/v1/wallet/lock"
    
    # Transaction endpoints
    BALANCE = "/api/v1/balance/{contract}"
    APPROVED_BALANCE = "/api/v1/balance/{contract}/{spender}"
    TRANSACTION = "/api/v1/transaction"
    SIGN_MESSAGE = "/api/v1/sign"
    
    # Token management
    ADD_TOKEN = "/api/v1/tokens/add"
    LIST_TOKENS = "/api/v1/tokens"
    
    # WebSocket
    WEBSOCKET = "/ws/v1"


# Error Codes
class ErrorCodes:
    """Standard error codes"""
    WALLET_LOCKED = "WALLET_LOCKED"
    UNAUTHORIZED = "UNAUTHORIZED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INVALID_REQUEST = "INVALID_REQUEST"
    NETWORK_ERROR = "NETWORK_ERROR"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    USER_REJECTED = "USER_REJECTED"
    WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
    INVALID_CONTRACT = "INVALID_CONTRACT"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    MAX_SESSIONS_EXCEEDED = "MAX_SESSIONS_EXCEEDED"
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
