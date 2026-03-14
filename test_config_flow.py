import requests
import json
import time

API_URL = "http://127.0.0.1:8001"
TOKEN = "EDPuVsjQSVWrQD81dbb2sxZqZ5as2AHhd7x8GTdwZtE"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def test_config_persistence():
    print("[-] Fetching current config...")
    try:
        r = requests.get(f"{API_URL}/config/", headers=HEADERS)
        if r.status_code != 200:
            print(f"[!] Failed to connect to API: {r.status_code}")
            return
        
        current_config = r.json()
        print(f"[*] Current Trade Qty: {current_config['discipline']['trade_qty']}")
        
        # Modify
        new_qty = current_config['discipline']['trade_qty'] + 1
        print(f"[-] Attempting to update Trade Qty to {new_qty}...")
        
        current_config['discipline']['trade_qty'] = new_qty
        
        # Send Update
        r = requests.put(f"{API_URL}/config/", json=current_config, headers=HEADERS)
        if r.status_code != 200:
            print(f"[!] Update Failed: {r.text}")
            return
            
        print("[*] Update Response OK. Verifying persistence...")
        
        # Verify via API
        r = requests.get(f"{API_URL}/config/", headers=HEADERS)
        updated_config = r.json()
        
        if updated_config['discipline']['trade_qty'] == new_qty:
            print("[SUCCESS] API reflects new config.")
        else:
            print(f"[FAIL] API returned old config: {updated_config['discipline']['trade_qty']}")
            
        # Verify File
        with open("data/user_config.json", "r") as f:
            file_config = json.load(f)
            if file_config['discipline']['trade_qty'] == new_qty:
                print("[SUCCESS] File persistence verified.")
            else:
                print(f"[FAIL] File content mismatch: {file_config['discipline']['trade_qty']}")
                
        # Revert
        print("[-] Reverting changes...")
        current_config['discipline']['trade_qty'] -= 1
        requests.put(f"{API_URL}/config/", json=current_config, headers=HEADERS)
        print("[*] Reverted.")
        
    except Exception as e:
        print(f"[!] Test Error: {e}")

if __name__ == "__main__":
    test_config_persistence()
