# RF Automation Backend - Architecture Documentation

## System Architecture

### High-Level Overview

```
┌─────────────────┐
│   Frontend       │  (Static web hosting - GitHub Pages style)
│   (Browser)      │
└────────┬─────────┘
         │ HTTPS/REST API
         │ JWT Authentication
         ▼
┌─────────────────────────────────────┐
│   RF Automation Backend             │
│   (FastAPI / Python)                │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Auth Module  │  │ Topology    │ │
│  │ (JWT)        │  │ Management  │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Ping Engine  │  │ Audit Log   │ │
│  │ (ICMP)       │  │ System      │ │
│  └──────────────┘  └─────────────┘ │
└────────┬───────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Database      │  (SQLite / PostgreSQL)
│   (SQLAlchemy)  │
└─────────────────┘
```

## Component Architecture

### 1. Authentication Module (`app/auth/`)

**Purpose**: Secure user authentication and authorization

**Components**:
- `models.py`: User, Role, AuditLog models
- `routes.py`: Login, logout, user management endpoints
- `utils.py`: Authentication utilities

**Security**:
- JWT tokens with expiration
- Bcrypt password hashing
- Role-based access control (Admin, NOC, Viewer)

**Flow**:
```
User → POST /auth/login → Verify credentials → Generate JWT → Return token
User → Protected endpoint → Validate JWT → Process request
```

### 2. Topology Management (`app/topology/`)

**Purpose**: Manage network topology (BTS/POP, IPs)

**Components**:
- `models.py`: BTSPOP, BaseIP, ClientIP, LoopbackIP, PingResult models
- `routes.py`: CRUD endpoints for topology
- `validators.py`: IP validation and gateway derivation

**Key Rules**:
- Gateway IP = Base IP - 1 (automatic, non-editable)
- /29 subnet logic enforced
- IP validation prevents injection

**Data Model**:
```
BTSPOP (1) ──< (many) BaseIP
BaseIP (1) ──< (many) ClientIP
BTSPOP (1) ──< (many) LoopbackIP
```

### 3. Ping Execution Engine (`app/ping/`)

**Purpose**: Execute real ICMP ping tests

**Components**:
- `executor.py`: Secure ping command execution
- `parser.py`: Parse ping output (Windows/Linux)
- `service.py`: Orchestrate ping execution
- `routes.py`: Ping API endpoint

**Execution Flow**:
```
1. User triggers: POST /execute/ping/{bts_id}
2. Service collects all IPs for BTS/POP
3. Execute pings in order:
   a. Gateway IPs (derived from Base IPs)
   b. Base IPs
   c. Client IPs
   d. Loopback IPs
4. Parse results
5. Store in database
6. Return structured JSON
```

**Security**:
- IP validation before execution
- No shell=True (prevents injection)
- Command built as list (not string)
- Timeout enforcement

**Ping Metrics Captured**:
- Packets Sent
- Packets Received
- Packet Loss %
- Min/Max/Avg RTT
- TTL
- Status (UP/DOWN/PARTIAL)

### 4. Database Layer (`app/db/`)

**Purpose**: Database configuration and session management

**Components**:
- `base.py`: SQLAlchemy engine and base
- `session.py`: Session utilities

**Database**:
- Development: SQLite
- Production: PostgreSQL (schema compatible)

### 5. Security Layer (`app/core/security.py`)

**Purpose**: Security utilities and middleware

**Features**:
- JWT token creation/verification
- Password hashing/verification
- IP address validation
- Input sanitization

### 6. Audit Logging (`app/audit/`)

**Purpose**: Security and compliance logging

**Features**:
- File-based audit logs
- Database audit table
- Event types: AUTH_SUCCESS, AUTH_FAILED, PING_EXECUTED, etc.

## Data Flow

### Ping Execution Flow

```
┌─────────────┐
│   Frontend  │
│   (User)    │
└──────┬──────┘
       │ POST /execute/ping/1
       │ Authorization: Bearer <token>
       ▼
┌─────────────────────────────────────┐
│   FastAPI Application              │
│   - Validate JWT                   │
│   - Rate limiting                  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Ping Service                      │
│   1. Get BTS/POP                    │
│   2. Get Base IPs                   │
│   3. Derive Gateway IPs             │
│   4. Get Client IPs                 │
│   5. Get Loopback IPs               │
└──────┬──────────────────────────────┘
       │
       │ For each IP (in order):
       ▼
┌─────────────────────────────────────┐
│   Ping Executor                     │
│   - Validate IP                     │
│   - Build command (list)             │
│   - Execute subprocess              │
│   - Capture output                  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Ping Parser                       │
│   - Parse output (OS-specific)      │
│   - Extract metrics                 │
│   - Determine status                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Database                          │
│   - Store PingResult                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Response                          │
│   - Structured JSON                 │
│   - Grouped by type                 │
└─────────────────────────────────────┘
```

## Security Architecture

### Authentication Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ POST /auth/login
     │ {username, password}
     ▼
┌─────────────────────┐
│  Auth Service       │
│  - Verify password  │
│  - Generate JWT      │
└────┬────────────────┘
     │ Return token
     ▼
┌─────────┐
│  User   │
│  (Token)│
└────┬────┘
     │ Request with token
     ▼
┌─────────────────────┐
│  Security Middleware│
│  - Validate JWT     │
│  - Extract user     │
└────┬────────────────┘
     │
     ▼
┌─────────────────────┐
│  Protected Endpoint │
└─────────────────────┘
```

### Security Controls

1. **Input Validation**
   - IP address format validation
   - Site name sanitization
   - SQL injection prevention (ORM)

2. **Command Injection Prevention**
   - No shell=True
   - Command as list, not string
   - IP validation before execution

3. **Authentication**
   - JWT tokens
   - Token expiration
   - Password hashing (bcrypt)

4. **Rate Limiting**
   - Per-IP rate limiting
   - Configurable limits

5. **Audit Logging**
   - All authentication events
   - All ping executions
   - All data changes

## API Contract

### Authentication Endpoints

- `POST /auth/login` - Login and get token
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout (client-side token removal)
- `POST /auth/users` - Create user (admin only)

### Topology Endpoints

- `POST /topology/bts-pop` - Create BTS/POP
- `GET /topology/bts-pop` - List BTS/POP
- `GET /topology/bts-pop/{id}` - Get BTS/POP
- `PUT /topology/bts-pop/{id}` - Update BTS/POP
- `DELETE /topology/bts-pop/{id}` - Delete BTS/POP

- `POST /topology/base-ip` - Create Base IP
- `GET /topology/base-ip` - List Base IPs

- `POST /topology/client-ip` - Create Client IP
- `GET /topology/client-ip` - List Client IPs
- `DELETE /topology/client-ip/{id}` - Delete Client IP

- `POST /topology/loopback-ip` - Create Loopback IP
- `GET /topology/loopback-ip` - List Loopback IPs
- `DELETE /topology/loopback-ip/{id}` - Delete Loopback IP

### Ping Execution

- `POST /execute/ping/{bts_id}` - Execute ping for BTS/POP

## Database Schema

### Entity Relationship

```
users (1) ──< (many) audit_logs
users (1) ──< (many) ping_results (indirect)

bts_pop (1) ──< (many) base_ip
bts_pop (1) ──< (many) loopback_ip
bts_pop (1) ──< (many) ping_results

base_ip (1) ──< (many) client_ip
base_ip (1) ──< (many) ping_results

client_ip (1) ──< (many) ping_results
```

## Deployment Architecture

### Development

```
Local Machine
├── Python 3.10+
├── SQLite Database
├── Virtual Environment
└── Uvicorn (dev server)
```

### Production

```
Production Server
├── Python 3.10+
├── PostgreSQL Database
├── Systemd Service
├── Nginx (reverse proxy)
├── SSL/TLS Certificate
└── Firewall Rules
```

## Network Architecture

```
┌─────────────────┐
│   Frontend      │  (Static hosting)
│   (Internet)    │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│   Backend       │  (Internal server)
│   (IIG/NTTN)    │
└────────┬────────┘
         │ ICMP Ping
         ▼
┌─────────────────┐
│   BTS/POP       │  (Target networks)
│   Networks      │
└─────────────────┘
```

## Error Handling

- Validation errors: 422 Unprocessable Entity
- Authentication errors: 401 Unauthorized
- Authorization errors: 403 Forbidden
- Not found: 404 Not Found
- Server errors: 500 Internal Server Error (details hidden in production)
- Rate limit: 429 Too Many Requests

## Logging Strategy

1. **Application Logs**: General application events
2. **Audit Logs**: Security and compliance events
3. **Request Logs**: All HTTP requests
4. **Error Logs**: Exceptions and errors

All logs are:
- Rotated (size-based)
- Time-stamped
- Structured
- Searchable

## Performance Considerations

- Database queries optimized with indexes
- Ping execution can be parallelized (future enhancement)
- Rate limiting prevents overload
- Connection pooling for database

## Scalability

- Stateless API (JWT tokens)
- Database can be scaled (PostgreSQL)
- Can deploy multiple backend instances behind load balancer
- Ping execution can be moved to worker queue (future enhancement)
