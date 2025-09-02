# Implementation Guide

This guide helps developers implement the Xian Universal Wallet Protocol in any programming language.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Implementation Checklist](#implementation-checklist)
3. [Language-Specific Examples](#language-specific-examples)
4. [Testing Your Implementation](#testing-your-implementation)
5. [Common Pitfalls](#common-pitfalls)

## Core Concepts

### Protocol Layers

```
┌─────────────────────────────────────┐
│         Application Layer           │  ← Your wallet logic
├─────────────────────────────────────┤
│         Protocol Layer              │  ← UWP implementation
├─────────────────────────────────────┤
│         Transport Layer             │  ← HTTP/WebSocket
└─────────────────────────────────────┘
```

### Session Lifecycle

1. **Authorization Request**: DApp requests access
2. **User Approval**: Wallet prompts user
3. **Session Creation**: Generate secure token
4. **Authenticated Requests**: Use bearer token
5. **Session Expiry**: Automatic cleanup

## Implementation Checklist

### Required Components

- [ ] HTTP server on configurable port (default: 8545)
- [ ] JSON request/response handling
- [ ] CORS headers for web compatibility
- [ ] Session token generation (256+ bits entropy)
- [ ] Permission validation system
- [ ] Rate limiting for security endpoints
- [ ] Input validation against schemas
- [ ] Error responses matching protocol codes

### Minimum Viable Implementation

```python
# Python example structure
class WalletProtocolServer:
    def __init__(self):
        self.sessions = {}  # token -> session data
        self.pending_requests = {}  # request_id -> auth request
        
    # Required endpoints
    async def get_wallet_status(self):
        return {"available": True, "locked": False, ...}
        
    async def request_authorization(self, request):
        request_id = generate_secure_id()
        self.pending_requests[request_id] = request
        return {"request_id": request_id, "status": "pending"}
        
    async def get_auth_status(self, request_id):
        # Check if approved/denied/pending
        pass
        
    async def get_wallet_info(self, session_token):
        # Validate session and return wallet info
        pass
        
    async def send_transaction(self, session_token, tx_request):
        # Validate session, check permissions, send tx
        pass
```

## Language-Specific Examples

### JavaScript/TypeScript (Node.js)

```javascript
import express from 'express';
import cors from 'cors';
import { randomBytes } from 'crypto';

const app = express();
app.use(cors());
app.use(express.json());

const sessions = new Map();
const pendingRequests = new Map();

// Status endpoint
app.get('/api/v1/wallet/status', (req, res) => {
  res.json({
    available: true,
    locked: false,
    wallet_type: 'web',
    version: '2.0.0'
  });
});

// Authorization request
app.post('/api/v1/auth/request', (req, res) => {
  const { app_name, app_url, permissions } = req.body;
  
  // Validate input
  if (!app_name || !app_url || !permissions?.length) {
    return res.status(400).json({
      error: 'Invalid request',
      code: 'INVALID_REQUEST'
    });
  }
  
  const requestId = randomBytes(16).toString('hex');
  pendingRequests.set(requestId, {
    app_name,
    app_url,
    permissions,
    status: 'pending'
  });
  
  res.status(202).json({
    request_id: requestId,
    status: 'pending'
  });
});

app.listen(8545, () => {
  console.log('Wallet protocol server running on port 8545');
});
```

### Rust (using Actix-web)

```rust
use actix_web::{web, App, HttpResponse, HttpServer, middleware};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

#[derive(Serialize)]
struct WalletStatus {
    available: bool,
    locked: bool,
    wallet_type: String,
    version: String,
}

#[derive(Deserialize)]
struct AuthRequest {
    app_name: String,
    app_url: String,
    permissions: Vec<String>,
    description: Option<String>,
}

struct AppState {
    sessions: Mutex<HashMap<String, Session>>,
    pending_requests: Mutex<HashMap<String, AuthRequest>>,
}

async fn get_wallet_status() -> HttpResponse {
    HttpResponse::Ok().json(WalletStatus {
        available: true,
        locked: false,
        wallet_type: "desktop".to_string(),
        version: "2.0.0".to_string(),
    })
}

async fn request_authorization(
    req: web::Json<AuthRequest>,
    data: web::Data<AppState>,
) -> HttpResponse {
    // Generate request ID
    let request_id = generate_request_id();
    
    // Store pending request
    let mut pending = data.pending_requests.lock().unwrap();
    pending.insert(request_id.clone(), req.into_inner());
    
    HttpResponse::Accepted().json(serde_json::json!({
        "request_id": request_id,
        "status": "pending"
    }))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let app_state = web::Data::new(AppState {
        sessions: Mutex::new(HashMap::new()),
        pending_requests: Mutex::new(HashMap::new()),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(middleware::DefaultHeaders::new()
                .header("Access-Control-Allow-Origin", "*"))
            .route("/api/v1/wallet/status", web::get().to(get_wallet_status))
            .route("/api/v1/auth/request", web::post().to(request_authorization))
    })
    .bind("127.0.0.1:8545")?
    .run()
    .await
}
```

### Go (using Gin)

```go
package main

import (
    "crypto/rand"
    "encoding/hex"
    "net/http"
    "sync"
    
    "github.com/gin-gonic/gin"
    "github.com/gin-contrib/cors"
)

type WalletServer struct {
    sessions        map[string]*Session
    pendingRequests map[string]*AuthRequest
    mu              sync.RWMutex
}

type AuthRequest struct {
    AppName     string   `json:"app_name" binding:"required"`
    AppURL      string   `json:"app_url" binding:"required"`
    Permissions []string `json:"permissions" binding:"required"`
    Description string   `json:"description"`
}

func (s *WalletServer) GetWalletStatus(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{
        "available":    true,
        "locked":       false,
        "wallet_type":  "desktop",
        "version":      "2.0.0",
    })
}

func (s *WalletServer) RequestAuthorization(c *gin.Context) {
    var req AuthRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{
            "error": "Invalid request",
            "code":  "INVALID_REQUEST",
        })
        return
    }
    
    // Generate request ID
    requestID := generateRequestID()
    
    // Store pending request
    s.mu.Lock()
    s.pendingRequests[requestID] = &req
    s.mu.Unlock()
    
    c.JSON(http.StatusAccepted, gin.H{
        "request_id": requestID,
        "status":     "pending",
    })
}

func generateRequestID() string {
    bytes := make([]byte, 16)
    rand.Read(bytes)
    return hex.EncodeToString(bytes)
}

func main() {
    server := &WalletServer{
        sessions:        make(map[string]*Session),
        pendingRequests: make(map[string]*AuthRequest),
    }
    
    r := gin.Default()
    r.Use(cors.Default())
    
    v1 := r.Group("/api/v1")
    {
        v1.GET("/wallet/status", server.GetWalletStatus)
        v1.POST("/auth/request", server.RequestAuthorization)
    }
    
    r.Run(":8545")
}
```

## Testing Your Implementation

### 1. Basic Connectivity Test

```bash
# Test wallet status
curl http://localhost:8545/api/v1/wallet/status

# Expected response:
# {
#   "available": true,
#   "locked": false,
#   "wallet_type": "desktop",
#   "version": "2.0.0"
# }
```

### 2. Authorization Flow Test

```bash
# Request authorization
curl -X POST http://localhost:8545/api/v1/auth/request \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "Test DApp",
    "app_url": "https://test.com",
    "permissions": ["wallet_info", "balance"]
  }'

# Check status
curl http://localhost:8545/api/v1/auth/status/{request_id}
```

### 3. Run Protocol Test Vectors

```python
import json
import httpx

# Load test vectors
with open('protocol/test-vectors/auth-flow.json') as f:
    test_vectors = json.load(f)

client = httpx.Client(base_url="http://localhost:8545")

for vector in test_vectors['vectors']:
    print(f"Testing: {vector['description']}")
    
    # Make request
    response = client.request(
        method=vector['request']['method'],
        url=vector['request']['path'],
        json=vector['request'].get('body'),
        headers=vector['request'].get('headers', {})
    )
    
    # Validate response
    assert response.status_code == vector['response']['status']
    # Additional validation...
```

## Common Pitfalls

### 1. Insufficient Entropy in Tokens

❌ **Wrong:**
```javascript
const token = Math.random().toString(36);  // Predictable!
```

✅ **Correct:**
```javascript
const token = crypto.randomBytes(32).toString('hex');  // 256 bits
```

### 2. Missing CORS Headers

❌ **Wrong:**
```python
# No CORS configuration
app = FastAPI()
```

✅ **Correct:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3. Improper Session Validation

❌ **Wrong:**
```python
def validate_session(token):
    return token in sessions  # No expiry check!
```

✅ **Correct:**
```python
def validate_session(token):
    session = sessions.get(token)
    if not session:
        return False
    if datetime.now() > session.expires_at:
        del sessions[token]
        return False
    return True
```

### 4. Incorrect Error Responses

❌ **Wrong:**
```javascript
res.status(400).send("Bad request");  // Plain text
```

✅ **Correct:**
```javascript
res.status(400).json({
    error: "Invalid request format",
    code: "INVALID_REQUEST",
    details: "Missing required field: app_name"
});
```

### 5. No Rate Limiting

❌ **Wrong:**
```python
@app.post("/api/v1/wallet/unlock")
async def unlock(password: str):
    # No rate limiting!
    return check_password(password)
```

✅ **Correct:**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/wallet/unlock")
@limiter.limit("5/minute")
async def unlock(request: Request, password: str):
    return check_password(password)
```

## Next Steps

1. **Implement Core Endpoints**: Start with the 5 required endpoints
2. **Add Security Features**: Rate limiting, input validation, secure tokens
3. **Test Compliance**: Run test vectors against your implementation
4. **Add Optional Features**: WebSocket support, additional endpoints
5. **Submit for Review**: Share your implementation with the community

## Getting Help

- Review the [Protocol Specification](../protocol/SPECIFICATION.md)
- Check the [Python Reference Implementation](../reference/python/)
- Ask questions in [GitHub Discussions](https://github.com/xian-network/xian-uwp/discussions)
- Join the [Discord Community](https://discord.gg/xian)