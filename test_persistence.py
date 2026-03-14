import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"
TOKEN = "EDPuVsjQSVWrQD81dbb2sxZqZ5as2AHhd7x8GTdwZtE"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

payload = {
    "signal_id": "TEST-SIG-X1",
    "symbol": "NIFTY",
    "direction": "CALL",
    "index_entry": 21500,
    "index_sl": 21450,
    "index_tp": 21600,
    "bar_time": "2026-01-31T23:59:00",
    "strategy": "RANGE_REJECTION",
    "rr": 2.5,
    "timestamp": int(time.time() * 1000)
}

def test_signal_post():
    print("Posting signal...")
    res = requests.post(f"{BASE_URL}/signal/", headers=HEADERS, json=payload)
    print(f"Status: {res.status_code}, Response: {res.json()}")
    return res.status_code == 200

def test_signal_get():
    print("Getting signals...")
    res = requests.get(f"{BASE_URL}/signal/", headers=HEADERS)
    signals = res.json()
    print(f"Signals found: {len(signals)}")
    for s in signals:
        if s.get("signal", {}).get("signal_id") == "TEST-SIG-X1":
            print("Verified: TEST-SIG-X1 found in feed.")
            return True
    return False

if __name__ == "__main__":
    if test_signal_post():
        time.sleep(1)
        test_signal_get()
