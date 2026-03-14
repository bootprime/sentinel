# Quick Start Guide

## Installation

1. **Install Python dependencies:**
   ```bash
   cd d:\Tools\Sentinel_v1.0
   pip install -r requirements.txt
   ```

2. **Set up Python path for tests:**
   ```bash
   # Add current directory to PYTHONPATH
   set PYTHONPATH=d:\Tools\Sentinel_v1.0
   
   # Or on Linux/Mac:
   export PYTHONPATH=/path/to/Sentinel_v1.0
   ```

3. **Run tests:**
   ```bash
   pytest tests/unit/ -v
   ```

## Running the Application

1. **Start backend:**
   ```bash
   python main.py
   ```
   
   Expected output:
   ```
   Sentinel System Starting Up...
   WebSocket heartbeat loop started
   Token refresh scheduler started
   Sentinel Prime Interface Ready. Waiting for signals...
   ```

2. **Start frontend:**
   ```bash
   cd frontend
   npm install  # First time only
   npm run dev
   ```

3. **Access dashboard:**
   Open browser to `http://localhost:5173`

## Verifying WebSocket Connection

1. Open browser console (F12)
2. Look for:
   ```
   [WebSocket] Connected to Sentinel backend
   [App] WebSocket connected
   ```

## Testing Token Refresh

The token refresh scheduler runs automatically every 5 minutes. To test manually:

```python
from core.broker.token_manager import token_manager
from core.broker.token_refresh import token_refresh_scheduler

# Register a test token
token_manager.register_token("KITE", "test_token_123")

# Check status
status = token_manager.get_expiry_status("KITE")
print(status)
```

## Running Tests with Coverage

```bash
# Run all tests with coverage
pytest --cov=core --cov=api --cov-report=html

# Open coverage report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
xdg-open htmlcov/index.html  # Linux
```

## Troubleshooting

### Import Error: No module named 'core'

**Solution:** Set PYTHONPATH to the project root:
```bash
set PYTHONPATH=d:\Tools\Sentinel_v1.0
```

### WebSocket Connection Failed

**Solution:** Ensure backend is running on port 8001:
```bash
python main.py
```

### Token Refresh Not Working

**Solution:** Check that the scheduler started:
```bash
# Look for this in logs:
Token refresh scheduler started
```
