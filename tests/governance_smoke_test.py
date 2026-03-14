import requests
import os
import json
import time

API_BASE = "http://127.0.0.1:8001"
TOKEN = os.getenv("SENTINEL_TOKEN", "EDPuVsjQSVWrQD81dbb2sxZqZ5as2AHhd7x8GTdwZtE") # Full token from secrets.json

def test_governance_pause():
    print("\n[1/2] Testing Manual Pause...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        response = requests.post(f"{API_BASE}/governance/pause", headers=headers)
        print(f"Response: {response.status_code} - {response.json()}")
        
        # Verify state via heartbeat
        hb = requests.get(f"{API_BASE}/heartbeat/").json()
        print(f"Current System State: {hb['system_state']}")
        assert hb['system_state'] == "MANUAL_PAUSE"
    except Exception as e:
        print(f"Pause Test Failed: {e}")

def test_governance_kill():
    print("\n[2/2] Testing Emergency Kill Switch...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        response = requests.post(f"{API_BASE}/governance/kill", headers=headers)
        print(f"Response: {response.status_code} - {response.json()}")
        
        # Verify state via heartbeat
        hb = requests.get(f"{API_BASE}/heartbeat/").json()
        print(f"Current System State: {hb['system_state']}")
        assert hb['system_state'] == "KILL_SWITCH"
        
        # Check logs for flattening event
        logs = requests.get(f"{API_BASE}/logs/?lines=5", headers=headers).json()
        messages = [l['message'] for l in logs]
        print(f"Recent Logs: {messages}")
        assert any("Kill Switch Activated" in m for m in messages)
    except Exception as e:
        print(f"Kill Switch Test Failed: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: SENTINEL_TOKEN environment variable not set.")
    else:
        test_governance_pause()
        test_governance_kill()
        print("\nGovernance Smoke Tests Completed.")
