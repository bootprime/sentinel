from fastapi import APIRouter, Query
from core.config import settings
from core.logger import LogLevel
import os
import json
from typing import List, Optional

router = APIRouter(prefix="/logs", tags=["Audit Logs"])

@router.get("/", response_model=List[dict])
async def get_logs(
    lines: int = 50, 
    level: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Retrieves the last N structured log entries.
    Filters:
    - level: USER | SYSTEM | AUDIT | DEBUG
    - category: SIGNAL | EXECUTION | RISK ...
    """
    log_path = f"{settings.DATA_DIR}/sentinel.log"
    if not os.path.exists(log_path):
        return [{"level": "SYSTEM", "message": "Log file not found. System starting...", "timestamp": ""}]
    
    logs = []
    try:
        with open(log_path, "r") as f:
            # Efficiently read last N lines
            # For simplicity in this v1, read all then slice. 
            # (Production would use `deque(f, lines)` or reverse reading)
            content = f.readlines()
            
            # Process strictly last N + buffer to handle multiline or filter
            start_index = max(0, len(content) - (lines * 5)) 
            recent_lines = content[start_index:]
            
            for line in recent_lines:
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        continue # Skip non-dict entries (e.g. plain strings)

                    if level:
                        req_level = level.upper()
                        entry_level = entry.get("level", "INFO")

                        # Strict Filtering based on UI Tabs
                        if req_level == "USER":
                            if entry_level != "USER": continue
                        elif req_level == "SYSTEM":
                            if entry_level not in ["SYSTEM", "INFO", "WARNING"]: continue
                        elif req_level == "AUDIT":
                            if entry_level != "AUDIT": continue
                        # DEBUG shows everything, so no filter needed
                        elif req_level != "DEBUG":
                            if entry_level != req_level: continue
                             
                    # 2. Category Filter
                    if category and entry.get("category") != category.upper():
                        continue
                        
                    logs.append(entry)
                    
                except json.JSONDecodeError:
                    continue # Skip malformed lines

            logs.reverse()
            return logs[:lines] # Return requested amount (now newest first)
    except Exception as e:
        return [{"level": "ERROR", "message": f"Failed to read logs: {str(e)}", "timestamp": ""}]
