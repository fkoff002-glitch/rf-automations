# RF Automation Backend

Production-grade Python backend for BTS/POP network topology management and automated ping testing in telco NOC environments.

## Features

- **Secure Authentication**: JWT-based authentication with role-based access control (Admin, NOC, Viewer)
- **Network Topology Management**: CRUD operations for BTS/POP sites, Base IPs, Client IPs, and Loopback IPs
- **Automatic Gateway Derivation**: Gateway IP = Base IP - 1 (non-negotiable rule)
- **Real ICMP Ping Execution**: Executes actual OS-level ping commands (4 packets)
- **Structured Results**: JSON responses grouped by BTS/POP with Gateway, Base, Client, and Loopback results
- **Security First**: OWASP Top 10 and SANS Top 30 compliant
- **Audit Logging**: Comprehensive audit trail for all operations
- **Rate Limiting**: Protection against brute force and DoS attacks

## Architecture

```
rf-automation-backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                   # Core configuration and utilities
│   │   ├── config.py          # Settings management
│   │   ├── security.py        # Authentication & security utilities
│   │   ├── logging.py         # Logging configuration
│   │   └── rate_limit.py      # Rate limiting middleware
│   ├── auth/                   # Authentication module
│   │   ├── models.py          # User and role models
│   │   ├── routes.py          # Auth API routes
│   │   └── utils.py           # Auth utilities
│   ├── topology/              # Network topology management
│   │   ├── models.py          # BTS/POP, IP models
│   │   ├── routes.py          # Topology CRUD routes
│   │   └── validators.py      # IP and data validation
│   ├── ping/                  # Ping execution engine
│   │   ├── executor.py        # Secure ping execution
│   │   ├── parser.py          # Ping output parser
│   │   ├── service.py         # Ping orchestration
│   │   └── routes.py          # Ping API routes
│   ├── db/                    # Database configuration
│   │   ├── base.py            # SQLAlchemy base
│   │   └── session.py         # Session management
│   └── audit/                 # Audit logging
│       └── logger.py          # Audit log system
├── alembic/                   # Database migrations
├── scripts/                   # Utility scripts
│   └── init_db.py            # Database initialization
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Database Schema

### Core Tables

- **users**: User accounts with roles (admin, noc, viewer)
- **roles**: Role definitions
- **bts_pop**: BTS or POP sites
- **base_ip**: Base IP addresses (Gateway = Base - 1)
- **client_ip**: Client IP addresses
- **loopback_ip**: Loopback IP addresses
- **ping_results**: Ping execution results
- **audit_logs**: Audit trail

## Installation

### Prerequisites

- Python 3.10 or higher
- pip
- ICMP ping capability (ping command available in PATH)
- Linux/Windows server with network access to BTS networks

### Setup

1. **Clone and navigate to project:**
   ```bash
   cd rf-automation-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY (minimum 32 characters)
   ```

5. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

6. **Run application:**
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, access:
- **Swagger UI**: `http://localhost:8000/docs` (if DEBUG=True)
- **ReDoc**: `http://localhost:8000/redoc` (if DEBUG=True)

### Authentication

All endpoints (except `/auth/login` and `/health`) require JWT authentication.

**Login:**
```bash
POST /auth/login
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin",
  "role": "admin"
}
```

**Use token in requests:**
```bash
Authorization: Bearer <access_token>
```

### Topology Management

**Create BTS/POP:**
```bash
POST /topology/bts-pop
{
  "name": "BTS-001",
  "site_type": "BTS",
  "location": "Location A",
  "description": "Base station 001"
}
```

**Create Base IP:**
```bash
POST /topology/base-ip
{
  "bts_pop_id": 1,
  "base_ip": "192.168.1.2",
  "description": "Base IP for BTS-001"
}
```
*Gateway IP (192.168.1.1) is automatically derived.*

**Create Client IP:**
```bash
POST /topology/client-ip
{
  "base_ip_id": 1,
  "client_ip": "192.168.1.3",
  "client_name": "Client-001"
}
```

**Create Loopback IP:**
```bash
POST /topology/loopback-ip
{
  "bts_pop_id": 1,
  "loopback_ip": "10.0.0.1"
}
```

### Ping Execution

**Execute ping for BTS/POP:**
```bash
POST /execute/ping/{bts_id}
```

**Response Structure:**
```json
{
  "bts_pop_id": 1,
  "bts_pop_name": "BTS-001",
  "site_type": "BTS",
  "execution_timestamp": "2024-01-15 10:30:00",
  "execution_duration_ms": 1250.5,
  "gateway": [
    {
      "ip_address": "192.168.1.1",
      "ip_type": "gateway",
      "packets_sent": 4,
      "packets_received": 4,
      "packet_loss_percent": 0.0,
      "min_rtt_ms": 1.2,
      "max_rtt_ms": 2.1,
      "avg_rtt_ms": 1.5,
      "ttl": 64,
      "status": "UP",
      "execution_duration_ms": 125.3
    }
  ],
  "base": [...],
  "clients": [...],
  "loopback": [...]
}
```

**Execution Order (STRICT):**
1. Gateway IPs (derived from Base IPs)
2. Base IPs
3. Client IPs
4. Loopback IPs

## Security Features

### OWASP Top 10 Mitigations

1. **A01:2021 – Broken Access Control**
   - JWT token-based authentication
   - Role-based access control (RBAC)
   - Protected endpoints

2. **A02:2021 – Cryptographic Failures**
   - Password hashing with bcrypt
   - JWT tokens with secure secret key
   - HTTPS recommended for production

3. **A03:2021 – Injection**
   - Parameterized queries (SQLAlchemy ORM)
   - IP validation before ping execution
   - No shell=True in subprocess calls
   - Input sanitization

4. **A04:2021 – Insecure Design**
   - Security by design
   - Authentication required from day 1
   - Audit logging enabled

5. **A05:2021 – Security Misconfiguration**
   - Environment-based configuration
   - No default credentials in production
   - Secure defaults

6. **A06:2021 – Vulnerable Components**
   - Regular dependency updates
   - Security-focused libraries

7. **A07:2021 – Authentication Failures**
   - Strong password hashing
   - Token expiration
   - Rate limiting on auth endpoints

8. **A08:2021 – Software and Data Integrity**
   - Input validation
   - Data integrity checks

9. **A09:2021 – Security Logging Failures**
   - Comprehensive audit logging
   - Request logging
   - Error logging

10. **A10:2021 – Server-Side Request Forgery**
    - IP validation
    - Allow-list enforcement

### SANS Top 30 Compliance

- Least privilege access
- Secure configuration management
- Comprehensive logging
- Input validation
- Secure coding practices

## Configuration

### Environment Variables

See `.env.example` for all configuration options:

- `SECRET_KEY`: JWT secret key (minimum 32 characters) - **REQUIRED**
- `DATABASE_URL`: Database connection string
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `PING_COUNT`: Number of ping packets (default: 4)
- `PING_TIMEOUT_SECONDS`: Ping timeout
- `RATE_LIMIT_PER_MINUTE`: Rate limit per IP
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Production Deployment

### Requirements

1. **Change default admin password** immediately
2. **Set strong SECRET_KEY** (minimum 32 characters, random)
3. **Use PostgreSQL** instead of SQLite
4. **Enable HTTPS** (use reverse proxy like nginx)
5. **Run as non-root user**
6. **Configure firewall** rules
7. **Set up log rotation**
8. **Enable monitoring** and alerting

### Systemd Service (Linux)

Create `/etc/systemd/system/rf-automation.service`:

```ini
[Unit]
Description=RF Automation Backend
After=network.target

[Service]
User=rf-automation
Group=rf-automation
WorkingDirectory=/opt/rf-automation-backend
Environment="PATH=/opt/rf-automation-backend/venv/bin"
ExecStart=/opt/rf-automation-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Network Requirements

- Backend server must have network access to BTS/POP networks
- ICMP (ping) must be allowed from backend to target networks
- Firewall rules should allow ping traffic

## Logging

- **Application logs**: `logs/app.log`
- **Audit logs**: `logs/audit.log`
- **Console output**: Structured logging to stdout

## Database Migrations

Using Alembic for database migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing

Manual testing steps:

1. **Authentication:**
   - Login with default admin credentials
   - Verify token is received
   - Test protected endpoint with token

2. **Topology:**
   - Create BTS/POP
   - Create Base IP (verify gateway derivation)
   - Create Client IPs
   - Create Loopback IP

3. **Ping Execution:**
   - Execute ping for BTS/POP
   - Verify execution order (Gateway → Base → Clients → Loopback)
   - Verify results structure
   - Check database for stored results

## Troubleshooting

### Ping fails

- Verify ICMP is allowed
- Check network connectivity
- Verify ping command is in PATH
- Check firewall rules

### Authentication fails

- Verify SECRET_KEY is set
- Check token expiration
- Verify user is active

### Database errors

- Check DATABASE_URL
- Verify database permissions
- Run migrations: `alembic upgrade head`

## License

Proprietary - Internal use only

## Support

For issues and questions, contact the development team.
