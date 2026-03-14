from core.logger import logger, LogCategory, LogLevel
import time

def test_logging():
    print("Testing Logging Layers...")
    
    # 1. User Log (Visible)
    logger.user(LogCategory.SIGNAL, "Signal Accepted: NIFTY 21500 CE", signal_id="TEST-001")
    
    # 2. System Log (Hidden by default)
    logger.system(LogCategory.EXECUTION, "Routing to KiteBroker...", signal_id="TEST-001")
    
    # 3. Audit Log (Security)
    logger.audit(LogCategory.SECURITY, "Token Rotation Detected", signal_id="SYSTEM")
    
    # 4. Debug Log (Dev only)
    try:
        1 / 0
    except Exception as e:
        logger.debug(LogCategory.SYSTEM, "Division by zero test", exc_info=True)

    print("Logs emitted. Check data/sentinel.log")

if __name__ == "__main__":
    test_logging()
