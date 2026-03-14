import json
import os
import csv
from datetime import datetime
from core.config import settings

class JournalManager:
    """
    Handles permanent records of all trade events.
    Stored in: 
    - journal.json (UI/Last 500 signals)
    - trade_audit.csv (Permanent Excel History)
    """
    
    JSON_PATH = os.path.join(settings.DATA_DIR, "journal.json")
    CSV_PATH = os.path.join(settings.DATA_DIR, "trade_audit.csv")
    
    @classmethod
    def log_event(cls, category: str, data: dict):
        timestamp = datetime.now().isoformat()
        
        # 1. JSON Logging (for UI/Dashboard)
        cls._log_json(category, data, timestamp)
        
        # 2. CSV Logging (for Excel History)
        cls._log_csv(category, data, timestamp)

    @classmethod
    def _log_json(cls, category, data, timestamp):
        event = {"timestamp": timestamp, "category": category, "data": data}
        journal = []
        if os.path.exists(cls.JSON_PATH):
            try:
                with open(cls.JSON_PATH, 'r') as f:
                    journal = json.load(f)
            except: journal = []
        
        journal.append(event)
        if len(journal) > 500: journal = journal[-500:]
        with open(cls.JSON_PATH, 'w') as f:
            json.dump(journal, f, indent=2)

    @classmethod
    def _log_csv(cls, category, data, timestamp):
        """Flat-maps data to a high-authority CSV row."""
        file_exists = os.path.exists(cls.CSV_PATH)
        headers = ["Timestamp", "Category", "SignalID", "Symbol", "Direction", 
                   "Strike", "Fill_Price", "Fill_Qty", "SL_Price", "TP_Price", "Status", "Reason", "Error"]
        
        # Flattening logic
        row = {
            "Timestamp": timestamp,
            "Category": category,
            "SignalID": data.get("signal_id") or data.get("signal", {}).get("signal_id", ""),
            "Symbol": data.get("signal", {}).get("symbol", ""),
            "Direction": data.get("signal", {}).get("direction", ""),
            "Strike": data.get("strike") or data.get("option", {}).get("strike", ""),
            "Fill_Price": data.get("fill", {}).get("price") or data.get("risk", {}).get("estimated_premium", ""),
            "Fill_Qty": data.get("fill", {}).get("qty", ""),
            "SL_Price": data.get("risk", {}).get("sl_price", ""),
            "TP_Price": data.get("risk", {}).get("tp_price", ""),
            "Status": data.get("status", ""),
            "Reason": data.get("reason", ""),
            "Error": data.get("error", "")
        }

        try:
            with open(cls.CSV_PATH, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            from core.logger import logger, LogCategory
            logger.audit(LogCategory.SYSTEM, f"CSV Journaling Failed: {str(e)}")

journal = JournalManager()
