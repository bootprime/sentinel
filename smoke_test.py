import requests
import json
import time
from datetime import datetime

URL = "http://127.0.0.1:8001/signal"
# Token from data/secrets.json
TOKEN = "EDPuVsjQSVWrQD81dbb2sxZqZ5as2AHhd7x8GTdwZtE"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Real-time signal with correct types for SignalPayload
signal = {
    "signal_id": f"REALTIME-LOG-{int(time.time())}",
    "timestamp": int(time.time() * 1000), # Epoch milliseconds as int
    "symbol": "BTCUSD",
    "strategy": "TREND_PULLBACK",
    "direction": "CALL",
    "index_entry": 50000.0,
    "index_sl": 49500.0,
    "index_tp": 51000.0,
    "bar_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "rr": 2.0
}

print(f"Sending dynamic test signal: {signal['signal_id']}")
try:
    response = requests.post(URL, json=signal, headers=HEADERS)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Success! Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error ({response.status_code}): {response.text}")
except Exception as e:
    print(f"Error: {e}")
