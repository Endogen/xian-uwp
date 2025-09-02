"""
Xian Wallet Protocol Server
Universal HTTP API server for all wallet implementations
"""

import asyncio
import hashlib
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import json
import secrets
import logging
import uvicorn

from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from xian_py.wallet import Wallet
from xian_py.xian_async import XianAsync
from xian_py.transaction import simulate_tx_async, get_nonce_async, create_tx, broadcast_tx_sync_async

from .models import (
    WalletType, Permission, ProtocolConfig, Endpoints, ErrorCodes, CORSConfig,
    AuthorizationRequest, TransactionRequest, SignMessageRequest, AddTokenRequest, UnlockRequest,
    WalletInfo, BalanceResponse, TransactionResult, SignatureResponse, 
    AuthorizationResponse, StatusResponse,
    Session, PendingRequest,
    RefreshTokenRequest, RefreshTokenResponse,
    DAppRegistration, DAppRegistrationResponse, DAppVerifyRequest, DAppInfo,
    DAppAlgorithm, DAppMetadata
)

from .client import WalletProtocolError
from .server_utils import RobustServerManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WalletProtocolServer:
    """Universal Wallet Protocol Server"""
    
    def __init__(
        self, 
        wallet_type: WalletType = WalletType.DESKTOP,
        cors_config: Optional[CORSConfig] = None,
        network_url: Optional[str] = None,
        chain_id: Optional[str] = None,
        wallet: Optional[Wallet] = None
    ):
        self.wallet_type = wallet_type
        self.uvicorn_server = None
        self.server_task = None
        self.is_running = False
        self.wallet = wallet
        self.xian_client: Optional[XianAsync] = None
        self.is_locked = True
        self.password_hash: Optional[str] = None
        self.password_hasher = PasswordHasher()
        
        # Robust server management
        self.server_manager: Optional[RobustServerManager] = None
        
        # CORS configuration
        self.cors_config = cors_config or CORSConfig.localhost_dev()
        
        # Network configuration (configurable, must be set before use)
        self.network_url = network_url
        self.chain_id = chain_id
        
        # Session management
        self.sessions: Dict[str, Session] = {}
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.websocket_connections: Set[WebSocket] = set()
        self.websocket_subscriptions: Dict[WebSocket, Set[str]] = {}  # websocket -> set of request_ids
        self.websocket_sessions: Dict[WebSocket, Session] = {}  # websocket -> session
        
        # Refresh token management
        self.refresh_tokens: Dict[str, Any] = {}  # refresh_token -> RefreshToken object
        self.enable_refresh_tokens = True
        self.refresh_token_lifetime = timedelta(days=7)
        self.rotate_refresh_tokens = True
        
        # DApp registry
        self.registered_dapps: Dict[str, Any] = {}  # dapp_id -> RegisteredDApp object
        self.enable_dapp_verification = True
        
        # Cache and activity tracking
        self.cache: Dict[str, tuple] = {}  # (data, timestamp)
        self.last_activity = datetime.now()
        
        # Rate limiting for unlock attempts
        self.unlock_attempts: Dict[str, Dict[str, Any]] = {}  # ip -> {attempts, last_attempt, locked_until}
        
        # Background task management
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Initialize FastAPI app
        self.app = self._create_app()
    
    def configure_network(self, network_url: str, chain_id: str):
        """Configure network settings"""
        self.network_url = network_url
        self.chain_id = chain_id
        logger.info(f"🌐 Network configured: {network_url} (chain: {chain_id})")
    
    def _validate_network_config(self):
        """Validate that network configuration is set"""
        if not self.network_url or not self.chain_id:
            raise WalletProtocolError("Network configuration not set. Call configure_network() first.")
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(_: FastAPI):
            logger.info("🚀 Xian Wallet Protocol Server starting...")
            # Initialize network client if wallet and network are configured
            if self.wallet and self.network_url:
                self.xian_client = XianAsync(self.network_url, wallet=self.wallet)
                logger.info(f"📍 Wallet initialized: {self.wallet.public_key}")
            # Start background tasks
            cleanup_task = asyncio.create_task(self._cleanup_task())
            self.background_tasks.add(cleanup_task)
            
            yield
            
            logger.info("💤 Xian Wallet Protocol Server shutting down...")
            # Cancel all background tasks gracefully
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for all tasks to complete cancellation
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            self.background_tasks.clear()
        
        app = FastAPI(
            title="Xian Wallet Protocol Server",
            description="Universal HTTP API for Xian wallet operations",
            version=ProtocolConfig.PROTOCOL_VERSION,
            lifespan=lifespan
        )
        
        # CORS middleware with configurable settings
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_config.allow_origins,
            allow_credentials=self.cors_config.allow_credentials,
            allow_methods=self.cors_config.allow_methods,
            allow_headers=self.cors_config.allow_headers,
            expose_headers=self.cors_config.expose_headers,
            max_age=self.cors_config.max_age,
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register API routes"""
        security = HTTPBearer()
        
        # Helper functions
        def verify_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Session:
            """Verify and return session"""
            token = credentials.credentials
            session = self.sessions.get(token)
            
            if not session:
                raise HTTPException(status_code=401, detail=ErrorCodes.UNAUTHORIZED)
            
            if datetime.now() > session.expires_at:
                del self.sessions[token]
                raise HTTPException(status_code=401, detail=ErrorCodes.SESSION_EXPIRED)
            
            # Update activity
            session.last_activity = datetime.now()
            self.last_activity = datetime.now()
            return session
        
        def require_permission(permission: Permission):
            """Decorator to require specific permission"""
            def wrapper(session: Session = Depends(verify_session)):
                if permission not in session.permissions:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                return session
            return wrapper
        
        def check_wallet_unlocked():
            """Check if wallet is unlocked"""
            if self.is_locked:
                raise HTTPException(status_code=423, detail=ErrorCodes.WALLET_LOCKED)
            if not self.wallet:
                raise HTTPException(status_code=404, detail=ErrorCodes.WALLET_NOT_FOUND)
        
        # Status endpoint (no auth required)
        @app.get(Endpoints.WALLET_STATUS, response_model=StatusResponse)
        async def get_wallet_status():
            """Get wallet status"""
            return StatusResponse(
                available=self.wallet is not None,
                locked=self.is_locked,
                wallet_type=self.wallet_type,
                network=self.network_url,
                chain_id=self.chain_id,
                version=ProtocolConfig.PROTOCOL_VERSION
            )
        
        # Authorization endpoints
        @app.post(Endpoints.AUTH_REQUEST)
        async def request_authorization(request: AuthorizationRequest):
            """Request DApp authorization"""
            # Enforce MAX_SESSIONS limit on pending requests
            if len(self.pending_requests) >= ProtocolConfig.MAX_SESSIONS:
                raise HTTPException(
                    status_code=429, 
                    detail=ErrorCodes.MAX_SESSIONS_EXCEEDED
                )
            
            request_id = secrets.token_urlsafe(16)
            
            # Verify DApp signature if provided
            signature_valid = None
            if self.enable_dapp_verification and request.dapp_id and request.signature:
                if request.dapp_id in self.registered_dapps:
                    dapp = self.registered_dapps[request.dapp_id]
                    # TODO: Implement actual signature verification
                    # For now, just check if DApp is registered
                    signature_valid = dapp.get("verified", False)
                    dapp["last_seen"] = datetime.now()
            
            pending_request = PendingRequest(
                request_id=request_id,
                app_name=request.app_name,
                app_url=request.app_url,
                permissions=request.permissions,
                description=request.description,
                created_at=datetime.now(),
                dapp_id=request.dapp_id,
                signature_valid=signature_valid
            )
            
            self.pending_requests[request_id] = pending_request
            
            # Notify wallet UI via WebSocket
            await self._broadcast_to_wallet({
                "type": "authorization_request",
                "request": pending_request.model_dump()
            })
            
            # Auto-cleanup after 5 minutes
            cleanup_task = asyncio.create_task(self._cleanup_request(request_id))
            self.background_tasks.add(cleanup_task)
            
            return {
                "request_id": request_id, 
                "status": "pending",
                "app_name": request.app_name
            }
        
        @app.get(Endpoints.AUTH_STATUS.replace("{request_id}", "{request_id}"))
        async def get_auth_status(request_id: str):
            """Get authorization request status"""
            pending_request = self.pending_requests.get(request_id)
            if not pending_request:
                # Check if it was approved (in sessions)
                for session in self.sessions.values():
                    if session.request_id == request_id:
                        return {"request_id": request_id, "status": "approved"}
                
                # Not found anywhere, might be denied or expired
                raise HTTPException(status_code=404, detail="Request not found")
            
            return {
                "request_id": request_id,
                "status": "pending",
                "app_name": pending_request.app_name,
                "app_url": pending_request.app_url,
                "permissions": pending_request.permissions,
                "description": pending_request.description
            }
        
        @app.get(Endpoints.AUTH_PENDING)
        async def list_pending_requests():
            """List all pending authorization requests"""
            pending_list = []
            for request_id, request in self.pending_requests.items():
                pending_list.append({
                    "request_id": request_id,
                    "status": "pending",
                    "app_name": request.app_name,
                    "app_url": request.app_url,
                    "permissions": request.permissions,
                    "description": request.description
                })
            return {"pending_requests": pending_list}
        
        @app.post(Endpoints.AUTH_APPROVE.replace("{request_id}", "{request_id}"))
        async def approve_authorization(request_id: str):
            """Approve authorization request"""
            pending_request = self.pending_requests.get(request_id)
            if not pending_request:
                raise HTTPException(status_code=404, detail="Request not found")
            
            # Create session
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(minutes=ProtocolConfig.SESSION_TIMEOUT_MINUTES)
            
            # Generate refresh token if enabled
            refresh_token = None
            refresh_expires_at = None
            if self.enable_refresh_tokens:
                refresh_token = secrets.token_urlsafe(32)
                refresh_expires_at = datetime.now() + self.refresh_token_lifetime
                
                self.refresh_tokens[refresh_token] = {
                    "token": refresh_token,
                    "session_token": session_token,
                    "app_name": pending_request.app_name,
                    "app_url": pending_request.app_url,
                    "permissions": pending_request.permissions,
                    "created_at": datetime.now(),
                    "expires_at": refresh_expires_at,
                    "last_used": None,
                    "dapp_id": pending_request.dapp_id,
                    "verified": pending_request.signature_valid or False
                }
            
            session = Session(
                token=session_token,
                app_name=pending_request.app_name,
                app_url=pending_request.app_url,
                permissions=pending_request.permissions,
                created_at=datetime.now(),
                expires_at=expires_at,
                last_activity=datetime.now(),
                request_id=request_id,
                refresh_token=refresh_token,
                dapp_id=pending_request.dapp_id,
                verified=pending_request.signature_valid or False
            )
            
            self.sessions[session_token] = session
            del self.pending_requests[request_id]
            
            # Broadcast approval via WebSocket
            await self._broadcast_to_wallet({
                "type": "authorization_approved",
                "request_id": request_id,
                "session_token": session_token,
                "app_name": pending_request.app_name
            })
            
            return AuthorizationResponse(
                session_token=session_token,
                expires_at=expires_at,
                permissions=pending_request.permissions,
                refresh_token=refresh_token,
                refresh_expires_at=refresh_expires_at
            )
        
        @app.post(Endpoints.AUTH_DENY.replace("{request_id}", "{request_id}"))
        async def deny_authorization(request_id: str):
            """Deny authorization request"""
            if request_id in self.pending_requests:
                pending_request = self.pending_requests[request_id]
                del self.pending_requests[request_id]
                
                # Broadcast denial via WebSocket
                await self._broadcast_to_wallet({
                    "type": "authorization_denied",
                    "request_id": request_id,
                    "app_name": pending_request.app_name
                })
                
            return {"status": "denied"}
        
        # Refresh token endpoints
        @app.post("/api/v1/auth/refresh")
        async def refresh_session(request: Request):
            """Refresh session using refresh token"""
            if not self.enable_refresh_tokens:
                raise HTTPException(status_code=404, detail="Refresh tokens not enabled")
            
            # Get refresh token from body
            body = await request.json()
            refresh_token = body.get("refresh_token")
            
            if not refresh_token or refresh_token not in self.refresh_tokens:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            
            refresh_obj = self.refresh_tokens[refresh_token]
            
            # Check if refresh token is expired
            if datetime.now() > refresh_obj["expires_at"]:
                del self.refresh_tokens[refresh_token]
                raise HTTPException(status_code=401, detail="Refresh token expired")
            
            # Generate new session token
            new_session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(minutes=ProtocolConfig.SESSION_TIMEOUT_MINUTES)
            
            # Create new session
            session = Session(
                token=new_session_token,
                app_name=refresh_obj["app_name"],
                app_url=refresh_obj["app_url"],
                permissions=refresh_obj["permissions"],
                created_at=datetime.now(),
                expires_at=expires_at,
                last_activity=datetime.now(),
                refresh_token=refresh_token if not self.rotate_refresh_tokens else None,
                dapp_id=refresh_obj.get("dapp_id"),
                verified=refresh_obj.get("verified", False)
            )
            
            self.sessions[new_session_token] = session
            
            # Rotate refresh token if enabled
            new_refresh_token = None
            new_refresh_expires = None
            if self.rotate_refresh_tokens:
                # Delete old refresh token
                del self.refresh_tokens[refresh_token]
                
                # Create new refresh token
                new_refresh_token = secrets.token_urlsafe(32)
                new_refresh_expires = datetime.now() + self.refresh_token_lifetime
                
                self.refresh_tokens[new_refresh_token] = {
                    "token": new_refresh_token,
                    "session_token": new_session_token,
                    "app_name": refresh_obj["app_name"],
                    "app_url": refresh_obj["app_url"],
                    "permissions": refresh_obj["permissions"],
                    "created_at": datetime.now(),
                    "expires_at": new_refresh_expires,
                    "last_used": datetime.now(),
                    "dapp_id": refresh_obj.get("dapp_id"),
                    "verified": refresh_obj.get("verified", False)
                }
                
                session.refresh_token = new_refresh_token
            else:
                # Update last used time
                refresh_obj["last_used"] = datetime.now()
                refresh_obj["session_token"] = new_session_token
            
            return {
                "session_token": new_session_token,
                "expires_at": expires_at.isoformat(),
                "refresh_token": new_refresh_token,
                "refresh_expires_at": new_refresh_expires.isoformat() if new_refresh_expires else None
            }
        
        @app.post("/api/v1/auth/revoke-refresh")
        async def revoke_refresh_token(request: Request):
            """Revoke a refresh token"""
            if not self.enable_refresh_tokens:
                raise HTTPException(status_code=404, detail="Refresh tokens not enabled")
            
            # Get refresh token from body
            body = await request.json()
            refresh_token = body.get("refresh_token")
            
            if refresh_token and refresh_token in self.refresh_tokens:
                # Also revoke associated session if exists
                refresh_obj = self.refresh_tokens[refresh_token]
                session_token = refresh_obj.get("session_token")
                if session_token and session_token in self.sessions:
                    del self.sessions[session_token]
                
                del self.refresh_tokens[refresh_token]
                return {"revoked": True}
            
            return {"revoked": False}
        
        # DApp registration endpoints
        @app.post("/api/v1/dapp/register")
        async def register_dapp(registration: DAppRegistration):
            """Register a DApp for identity verification"""
            if not self.enable_dapp_verification:
                raise HTTPException(status_code=404, detail="DApp verification not enabled")
            
            # Generate unique DApp ID
            dapp_id = f"dapp_{secrets.token_urlsafe(16)}"
            
            # Store DApp registration
            self.registered_dapps[dapp_id] = {
                "dapp_id": dapp_id,
                "app_name": registration.app_name,
                "app_url": registration.app_url,
                "public_key": registration.public_key,
                "algorithm": registration.algorithm,
                "metadata": registration.metadata,
                "registered_at": datetime.now(),
                "verified": False
            }
            
            # Generate challenge for verification
            challenge = secrets.token_urlsafe(32)
            
            return {
                "dapp_id": dapp_id,
                "registered_at": datetime.now().isoformat(),
                "challenge": challenge,
                "verification_required": True
            }
        
        @app.post("/api/v1/dapp/verify")
        async def verify_dapp(verification: DAppVerifyRequest):
            """Verify DApp signature"""
            if not self.enable_dapp_verification:
                raise HTTPException(status_code=404, detail="DApp verification not enabled")
            
            if verification.dapp_id not in self.registered_dapps:
                raise HTTPException(status_code=404, detail="DApp not found")
            
            dapp = self.registered_dapps[verification.dapp_id]
            
            # TODO: Implement actual signature verification based on algorithm
            # For now, just mark as verified
            dapp["verified"] = True
            dapp["last_seen"] = datetime.now()
            
            return {
                "verified": True,
                "dapp_id": verification.dapp_id,
                "trust_level": "signature_verified"
            }
        
        @app.get("/api/v1/dapp/{dapp_id}")
        async def get_dapp_info(dapp_id: str):
            """Get DApp information"""
            if not self.enable_dapp_verification:
                raise HTTPException(status_code=404, detail="DApp verification not enabled")
            
            if dapp_id not in self.registered_dapps:
                raise HTTPException(status_code=404, detail="DApp not found")
            
            dapp = self.registered_dapps[dapp_id]
            
            return {
                "dapp_id": dapp_id,
                "app_name": dapp["app_name"],
                "app_url": dapp["app_url"],
                "verified": dapp.get("verified", False),
                "trust_level": "signature_verified" if dapp.get("verified") else "unverified",
                "registered_at": dapp["registered_at"].isoformat(),
                "last_seen": dapp.get("last_seen", dapp["registered_at"]).isoformat()
            }
        
        # Wallet endpoints
        @app.get(Endpoints.WALLET_INFO, response_model=WalletInfo)
        async def get_wallet_info(_: Session = Depends(require_permission(Permission.WALLET_INFO))):
            """Get wallet information"""
            # Wallet info should be available even when locked - only check wallet exists
            if not self.wallet:
                raise HTTPException(status_code=404, detail=ErrorCodes.WALLET_NOT_FOUND)
            
            cache_key = "wallet_info"
            cached_data = self._get_cached(cache_key, ttl_seconds=60)
            
            if cached_data:
                return cached_data
            
            wallet_info = WalletInfo(
                address=self.wallet.public_key,
                truncated_address=f"{self.wallet.public_key[:8]}...{self.wallet.public_key[-8:]}",
                locked=self.is_locked,
                chain_id=self.chain_id,
                network=self.network_url,
                wallet_type=self.wallet_type
            )
            
            self._set_cache(cache_key, wallet_info)
            return wallet_info
        
        @app.post(Endpoints.WALLET_UNLOCK)
        async def unlock_wallet(request: UnlockRequest, req: Request):
            """Unlock wallet with rate limiting"""
            if not self.password_hash:
                raise HTTPException(status_code=400, detail="No password set")
            
            # Get client IP
            client_ip = req.client.host if req.client else "unknown"
            
            # Check rate limiting
            now = datetime.now()
            if client_ip in self.unlock_attempts:
                attempt_info = self.unlock_attempts[client_ip]
                
                # Check if account is locked
                if attempt_info.get("locked_until") and now < attempt_info["locked_until"]:
                    remaining_seconds = int((attempt_info["locked_until"] - now).total_seconds())
                    raise HTTPException(
                        status_code=429,
                        detail=f"{ErrorCodes.ACCOUNT_LOCKED}: Too many failed attempts. Try again in {remaining_seconds} seconds."
                    )
                
                # Check if we need to enforce delay between attempts
                if attempt_info.get("last_attempt"):
                    time_since_last = (now - attempt_info["last_attempt"]).total_seconds()
                    required_delay = min(2 ** (attempt_info.get("attempts", 0) - 1), 60)  # Exponential backoff, max 60s
                    
                    if time_since_last < required_delay:
                        raise HTTPException(
                            status_code=429,
                            detail=f"{ErrorCodes.TOO_MANY_ATTEMPTS}: Please wait {int(required_delay - time_since_last)} seconds before trying again."
                        )
            
            # Verify password using Argon2
            try:
                self.password_hasher.verify(self.password_hash, request.password)
                # Password is correct
            except (VerifyMismatchError, Exception):
                # Track failed attempt
                if client_ip not in self.unlock_attempts:
                    self.unlock_attempts[client_ip] = {"attempts": 0, "last_attempt": None, "locked_until": None}
                
                self.unlock_attempts[client_ip]["attempts"] += 1
                self.unlock_attempts[client_ip]["last_attempt"] = now
                
                # Lock account after 5 failed attempts
                if self.unlock_attempts[client_ip]["attempts"] >= 5:
                    self.unlock_attempts[client_ip]["locked_until"] = now + timedelta(minutes=15)
                    logger.warning(f"Account locked for IP {client_ip} after 5 failed unlock attempts")
                
                raise HTTPException(status_code=401, detail="Invalid password")
            
            # Successful unlock - clear rate limiting for this IP
            if client_ip in self.unlock_attempts:
                del self.unlock_attempts[client_ip]
            
            self.is_locked = False
            self.last_activity = datetime.now()
            self._clear_cache()
            
            return {"status": "unlocked"}
        
        @app.post(Endpoints.WALLET_LOCK)
        async def lock_wallet():
            """Lock wallet"""
            self.is_locked = True
            self._clear_cache()
            return {"status": "locked"}
        
        # Balance endpoints
        @app.get(Endpoints.BALANCE.replace("{contract}", "{contract}"), response_model=BalanceResponse)
        async def get_balance(contract: str, _: Session = Depends(require_permission(Permission.BALANCE))):
            """Get token balance"""
            # Balance contains sensitive financial information - require unlocked wallet
            check_wallet_unlocked()
            
            cache_key = f"balance_{contract}_{self.wallet.public_key}"
            cached_data = self._get_cached(cache_key, ttl_seconds=10)
            
            if cached_data:
                return cached_data
            
            try:
                if not self.xian_client:
                    raise HTTPException(status_code=503, detail="Network client not configured")
                
                balance = await self.xian_client.get_balance(self.wallet.public_key, contract=contract)
                response = BalanceResponse(balance=balance, contract=contract)
                self._set_cache(cache_key, response)
                return response
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Transaction endpoints
        @app.post(Endpoints.TRANSACTION, response_model=TransactionResult)
        async def send_transaction(request: TransactionRequest, _: Session = Depends(require_permission(Permission.TRANSACTIONS))):
            """Send transaction"""
            check_wallet_unlocked()
            self._validate_network_config()
            
            try:
                nonce = await get_nonce_async(self.network_url, self.wallet.public_key)
                
                payload = {
                    "chain_id": self.chain_id,
                    "contract": request.contract,
                    "function": request.function,
                    "kwargs": request.kwargs,
                    "nonce": nonce,
                    "sender": self.wallet.public_key,
                    "stamps_supplied": request.stamps_supplied or 0
                }
                
                # Estimate stamps if not provided
                if not request.stamps_supplied:
                    simulated = await simulate_tx_async(self.network_url, payload)
                    payload["stamps_supplied"] = simulated.get("stamps_used", 50000)
                
                # Create and broadcast transaction
                tx = create_tx(payload, self.wallet)
                result = await broadcast_tx_sync_async(self.network_url, tx)
                
                # Clear balance cache after transaction
                self._clear_cache_pattern("balance_")
                
                return TransactionResult(
                    success=True,
                    transaction_hash=tx.get("hash"),
                    result=result,
                    gas_used=payload["stamps_supplied"]
                )
            except Exception as e:
                return TransactionResult(
                    success=False,
                    errors=[str(e)]
                )
        
        @app.post(Endpoints.SIGN_MESSAGE, response_model=SignatureResponse)
        async def sign_message(request: SignMessageRequest, _: Session = Depends(require_permission(Permission.SIGN_MESSAGE))):
            """Sign message"""
            check_wallet_unlocked()
            
            try:
                signature = self.wallet.sign_msg(request.message)
                return SignatureResponse(
                    signature=signature,
                    message=request.message,
                    address=self.wallet.public_key
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Token management
        @app.post(Endpoints.ADD_TOKEN)
        async def add_token(request: AddTokenRequest, _: Session = Depends(require_permission(Permission.ADD_TOKEN))):
            """Add token to wallet"""
            # In full implementation, this would add to wallet's token list
            return {"accepted": True, "contract": request.contract_address}
        
        # WebSocket endpoint
        @app.websocket(Endpoints.WEBSOCKET)
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time communication with authentication"""
            # Extract token from headers or query params
            token = None
            
            # Try to get token from Authorization header
            auth_header = websocket.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            
            # Fallback to query parameter
            if not token:
                token = websocket.query_params.get("token")
            
            # Verify token
            if not token or token not in self.sessions:
                await websocket.close(code=1008, reason="Unauthorized")
                return
            
            session = self.sessions.get(token)
            if datetime.now() > session.expires_at:
                del self.sessions[token]
                await websocket.close(code=1008, reason="Session expired")
                return
            
            await websocket.accept()
            self.websocket_connections.add(websocket)
            self.websocket_subscriptions[websocket] = set()
            self.websocket_sessions[websocket] = session
            
            try:
                while True:
                    # Check if session is still valid
                    if token not in self.sessions or datetime.now() > session.expires_at:
                        await websocket.close(code=1008, reason="Session expired")
                        break
                    
                    data = await websocket.receive_text()
                    try:
                        message = json.loads(data)
                        
                        # Update session activity
                        session.last_activity = datetime.now()
                        
                        # Handle ping/pong
                        if message.get("type") == "ping":
                            await websocket.send_text('{"type":"pong"}')
                        
                        # Handle subscription to authorization requests
                        elif message.get("type") == "subscribe":
                            request_id = message.get("request_id")
                            if request_id:
                                self.websocket_subscriptions[websocket].add(request_id)
                                await websocket.send_text(json.dumps({
                                    "type": "subscribed",
                                    "request_id": request_id
                                }))
                        
                        # Handle unsubscription
                        elif message.get("type") == "unsubscribe":
                            request_id = message.get("request_id")
                            if request_id and websocket in self.websocket_subscriptions:
                                self.websocket_subscriptions[websocket].discard(request_id)
                                await websocket.send_text(json.dumps({
                                    "type": "unsubscribed",
                                    "request_id": request_id
                                }))
                                
                    except json.JSONDecodeError:
                        # Invalid JSON message, ignore
                        pass
                            
            except WebSocketDisconnect:
                self.websocket_connections.discard(websocket)
                if websocket in self.websocket_subscriptions:
                    del self.websocket_subscriptions[websocket]
                if websocket in self.websocket_sessions:
                    del self.websocket_sessions[websocket]
    
    # Cache management
    def _get_cached(self, key: str, ttl_seconds: int) -> Optional[Any]:
        """Get cached data if still valid"""
        if key not in self.cache:
            return None
        
        data, timestamp = self.cache[key]
        if (datetime.now() - timestamp).total_seconds() > ttl_seconds:
            del self.cache[key]
            return None
        
        return data
    
    def _set_cache(self, key: str, data: Any):
        """Set cache data"""
        self.cache[key] = (data, datetime.now())
    
    def _clear_cache(self):
        """Clear all cache"""
        self.cache.clear()
    
    def _clear_cache_pattern(self, pattern: str):
        """Clear cache entries matching pattern"""
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]
    
    def _cleanup_rate_limits(self):
        """Clean up expired rate limit entries"""
        now = datetime.now()
        ips_to_remove = []
        
        for ip, info in self.unlock_attempts.items():
            # Remove entries that haven't been used for 30 minutes
            if info.get("last_attempt"):
                if (now - info["last_attempt"]).total_seconds() > 1800:  # 30 minutes
                    ips_to_remove.append(ip)
            # Remove entries where lock has expired
            elif info.get("locked_until") and now > info["locked_until"]:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del self.unlock_attempts[ip]
    
    # WebSocket helpers
    async def _broadcast_to_wallet(self, message: dict):
        """Broadcast message to wallet UI and subscribed clients"""
        
        if self.websocket_connections:
            disconnected = set()
            message_str = json.dumps(message)
            
            # Check if this is an authorization-related message
            message_type = message.get("type", "")
            request_id = message.get("request_id")
            
            for websocket in self.websocket_connections:
                try:
                    # For authorization messages, only send to subscribed clients
                    if message_type in ["authorization_approved", "authorization_denied"] and request_id:
                        if websocket in self.websocket_subscriptions and request_id in self.websocket_subscriptions[websocket]:
                            await websocket.send_text(message_str)
                    else:
                        # For other messages (like authorization_request), broadcast to all
                        await websocket.send_text(message_str)
                except:
                    disconnected.add(websocket)
            
            # Remove disconnected websockets
            self.websocket_connections -= disconnected
            for ws in disconnected:
                if ws in self.websocket_subscriptions:
                    del self.websocket_subscriptions[ws]
    
    # Background tasks
    async def _cleanup_task(self):
        """Background cleanup task"""
        try:
            while True:
                await asyncio.sleep(60)  # Run every minute
                
                # Clean expired sessions
                now = datetime.now()
                expired_tokens = [
                    token for token, session in self.sessions.items()
                    if now > session.expires_at
                ]
                for token in expired_tokens:
                    del self.sessions[token]
                
                # Clean old pending requests
                expired_requests = [
                    req_id for req_id, request in self.pending_requests.items()
                    if (now - request.created_at).total_seconds() > 300  # 5 minutes
                ]
                for req_id in expired_requests:
                    del self.pending_requests[req_id]
                
                # Clean up expired rate limits
                self._cleanup_rate_limits()
                
                # Auto-lock on inactivity
                if not self.is_locked and self.last_activity:
                    inactive_time = now - self.last_activity
                    if inactive_time.total_seconds() > ProtocolConfig.AUTO_LOCK_MINUTES * 60:
                        self.is_locked = True
                        self._clear_cache()
                        logger.info("Wallet auto-locked due to inactivity")
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled during shutdown")
            raise
    
    async def _cleanup_request(self, request_id: str):
        """Cleanup specific request after timeout"""
        try:
            await asyncio.sleep(300)  # 5 minutes
            self.pending_requests.pop(request_id, None)
        except asyncio.CancelledError:
            # Clean up the request immediately on cancellation
            self.pending_requests.pop(request_id, None)
            # Remove self from background tasks
            current_task = asyncio.current_task()
            self.background_tasks.discard(current_task)
    
    # Wallet management
    def set_wallet(self, wallet: Wallet, password_hash: Optional[str] = None):
        """Set the wallet instance and optional password hash"""
        self.wallet = wallet
        if password_hash:
            self.password_hash = password_hash
        
        # Initialize network client if network is configured
        if self.network_url:
            self.xian_client = XianAsync(self.network_url, wallet=self.wallet)
            logger.info(f"📍 Wallet configured: {self.wallet.public_key}")
    
    def lock_wallet(self):
        """Lock the wallet"""
        self.is_locked = True
        logger.info("🔒 Wallet locked")
    
    def unlock_wallet(self, password: str) -> bool:
        """Unlock the wallet with password"""
        if not self.password_hash:
            raise HTTPException(status_code=400, detail="No password set for wallet")
        
        provided_hash = hashlib.sha256(password.encode()).hexdigest()
        if provided_hash == self.password_hash:
            self.is_locked = False
            logger.info("🔓 Wallet unlocked")
            return True
        return False
    
    def run(
        self, 
        host: str = ProtocolConfig.DEFAULT_HOST, 
        port: int = ProtocolConfig.DEFAULT_PORT,
        allow_any_host: bool = False,
        force_cleanup: bool = False
    ):
        """Run the server (blocking call) with robust startup"""
        # Allow binding to any host for web deployment scenarios
        if allow_any_host:
            host = "0.0.0.0"

        # Use asyncio to handle robust startup
        asyncio.run(self._run_with_robust_startup(host, port, force_cleanup))

    async def _run_with_robust_startup(self, host: str, port: int, force_cleanup: bool):
        """Internal method to run server with robust startup"""
        self.server_manager = RobustServerManager(host, port)
        
        # Ensure port is available
        success, message = await self.server_manager.prepare_startup(force_cleanup)
        logger.info(self.server_manager.get_startup_message(success, message))
        
        if not success and not force_cleanup:
            raise RuntimeError(f"Cannot start server: {message}")
        
        logger.info(f"🌐 Starting server on {host}:{port}")
        logger.info(f"🔒 CORS origins: {self.cors_config.allow_origins}")

        # Create uvicorn server instance with socket reuse
        config = uvicorn.Config(
            self.app, 
            host=host, 
            port=port, 
            log_level="info",
            # Enable socket reuse for robust restarts
            access_log=False  # Reduce log noise
        )
        self.uvicorn_server = uvicorn.Server(config)
        self.is_running = True

        # Run the server (blocking)
        await self.uvicorn_server.serve()
        
    async def start_async(
        self,
        host: str = ProtocolConfig.DEFAULT_HOST,
        port: int = ProtocolConfig.DEFAULT_PORT,
        allow_any_host: bool = False,
        force_cleanup: bool = False
    ):
        """Start the server asynchronously with robust startup"""
        if allow_any_host:
            host = "0.0.0.0"
        
        # Initialize server manager
        self.server_manager = RobustServerManager(host, port)
        
        # Ensure port is available
        success, message = await self.server_manager.prepare_startup(force_cleanup)
        logger.info(self.server_manager.get_startup_message(success, message))
        
        if not success and not force_cleanup:
            raise RuntimeError(f"Cannot start server: {message}")
            
        logger.info(f"🌐 Starting server on {host}:{port}")
        logger.info(f"🔒 CORS origins: {self.cors_config.allow_origins}")
        
        # Create uvicorn server instance with socket reuse
        config = uvicorn.Config(
            self.app, 
            host=host, 
            port=port, 
            log_level="info",
            access_log=False  # Reduce log noise
        )
        self.uvicorn_server = uvicorn.Server(config)
        self.is_running = True
        
        # Start server in background task
        self.server_task = asyncio.create_task(self.uvicorn_server.serve())
        
    async def stop_async(self):
        """Stop the server asynchronously"""
        if self.uvicorn_server and self.is_running:
            logger.info("🛑 Stopping server...")
            self.uvicorn_server.should_exit = True
            
            if self.server_task:
                self.server_task.cancel()
                try:
                    await asyncio.wait_for(self.server_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                    
            logger.info("✅ Server stopped")
        
        # Always set is_running to False when stop is called
        self.is_running = False
            
    def stop(self):
        """Stop the server (synchronous wrapper)"""
        if self.uvicorn_server and self.is_running:
            logger.info("🛑 Stopping server...")
            self.is_running = False
            self.uvicorn_server.should_exit = True
            logger.info("✅ Server stop requested")
            
    def is_server_running(self):
        """Check if server is currently running"""
        return self.is_running and self.uvicorn_server is not None
    
    def run_robust(
        self,
        host: str = ProtocolConfig.DEFAULT_HOST,
        port: int = ProtocolConfig.DEFAULT_PORT,
        allow_any_host: bool = False,
        max_retries: int = 3
    ):
        """
        Run server with robust startup that handles port conflicts automatically
        
        This method will:
        1. Check if port is in use
        2. If in use, check if existing server is responsive
        3. If unresponsive, clean up and start new server
        4. Retry up to max_retries times
        """
        for attempt in range(max_retries):
            try:
                # On first attempt, try without force cleanup
                # On subsequent attempts, use force cleanup
                force_cleanup = attempt > 0
                
                logger.info(f"🚀 Server startup attempt {attempt + 1}/{max_retries}")
                self.run(host=host, port=port, allow_any_host=allow_any_host, force_cleanup=force_cleanup)
                return  # Success!
                
            except Exception as e:
                logger.warning(f"Startup attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ Failed to start server after {max_retries} attempts")
                    raise
                else:
                    logger.info(f"🔄 Retrying in 2 seconds...")
                    import time
                    time.sleep(2)
    
    async def start_async_robust(
        self,
        host: str = ProtocolConfig.DEFAULT_HOST,
        port: int = ProtocolConfig.DEFAULT_PORT,
        allow_any_host: bool = False,
        max_retries: int = 3
    ):
        """
        Start server asynchronously with robust startup that handles port conflicts automatically
        """
        for attempt in range(max_retries):
            try:
                # On first attempt, try without force cleanup
                # On subsequent attempts, use force cleanup
                force_cleanup = attempt > 0
                
                logger.info(f"🚀 Async server startup attempt {attempt + 1}/{max_retries}")
                await self.start_async(host=host, port=port, allow_any_host=allow_any_host, force_cleanup=force_cleanup)
                return  # Success!
                
            except Exception as e:
                logger.warning(f"Async startup attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ Failed to start async server after {max_retries} attempts")
                    raise
                else:
                    logger.info(f"🔄 Retrying in 2 seconds...")
                    await asyncio.sleep(2)


def create_server(
    wallet_type: WalletType = WalletType.DESKTOP,
    cors_config: Optional[CORSConfig] = None
) -> WalletProtocolServer:
    """Factory function to create server instance"""
    return WalletProtocolServer(wallet_type=wallet_type, cors_config=cors_config)


if __name__ == "__main__":
    server = create_server()
    server.run()
