# Quick Start Guide

## Prerequisites

- Python 3.10+
- pip
- ping command available in PATH

## Setup (5 minutes)

1. **Navigate to project:**
   ```bash
   cd rf-automation-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file:**
   ```bash
   # Create .env file with at minimum:
   SECRET_KEY=your-super-secret-key-minimum-32-characters-long-change-this
   DATABASE_URL=sqlite:///./rf_automation.db
   ```

5. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

6. **Start server:**
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Default Credentials

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **CHANGE THIS IN PRODUCTION!**

## Test the API

1. **Login:**
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```

2. **Get token from response and use it:**
   ```bash
   export TOKEN="your-token-here"
   ```

3. **Create BTS/POP:**
   ```bash
   curl -X POST "http://localhost:8000/topology/bts-pop" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "BTS-001", "site_type": "BTS"}'
   ```

4. **Create Base IP:**
   ```bash
   curl -X POST "http://localhost:8000/topology/base-ip" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"bts_pop_id": 1, "base_ip": "192.168.1.2"}'
   ```
   *Gateway IP (192.168.1.1) is automatically derived.*

5. **Execute Ping:**
   ```bash
   curl -X POST "http://localhost:8000/execute/ping/1" \
     -H "Authorization: Bearer $TOKEN"
   ```

## API Documentation

Once server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

**Import errors:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Database errors:**
- Run: `python scripts/init_db.py`
- Check DATABASE_URL in .env

**Ping fails:**
- Verify ping command works: `ping -c 4 8.8.8.8`
- Check network connectivity
- Verify ICMP is allowed

**Authentication fails:**
- Check SECRET_KEY is set in .env (min 32 chars)
- Verify credentials are correct

## Next Steps

1. Read full [README.md](README.md)
2. Review [ARCHITECTURE.md](ARCHITECTURE.md)
3. Change default admin password
4. Configure for production
