import time
from core.config import settings, SystemMode
from core.contract import SignalPayload
from core.state import state_engine, SystemStateEnum
from core.logger import logger, LogCategory
from core.execution import ExecutionIntent
from broker.base import BaseBroker
from broker.null import NullBroker

# Simple Factory for now
def get_broker() -> BaseBroker:
    if settings.MODE == SystemMode.PAPER:
        return NullBroker()
    # Logic for REAL broker would go here
    return NullBroker() # Default fallback

class ExecutionEngine:
    def __init__(self):
        self.broker = get_broker()

    def execute(self, signal: SignalPayload):
        logger.system(LogCategory.EXECUTION, f"Execution Engine received signal: {signal.signal_id}", signal_id=signal.signal_id)
        
        # 1. Final State Check
        if state_engine.current.state != SystemStateEnum.READY:
            logger.system(LogCategory.STATE, f"Execution Blocked: State is {state_engine.current.state}", signal_id=signal.signal_id)
            return False

        try:
            # 2. Sizing Logic (Hypercare: Fixed 1 lot or Config Max)
            quantity = settings.MAX_QUANTITY_LIMIT
            
            # 3. Create Intent
            intent = ExecutionIntent(
                signal=signal,
                quantity=quantity,
                broker_name=self.broker.__class__.__name__,
                timestamp=time.time()
            )
            
            # 4. Execute via Broker
            logger.system(LogCategory.EXECUTION, f"Executing Intent: {intent}", signal_id=signal.signal_id)
            result = self.broker.place_order(signal, quantity)
            
            # 5. Log Success
            logger.user(LogCategory.EXECUTION, f"Order Placed Successfully. ID: {result.get('order_id')}", signal_id=signal.signal_id)
            
            # 6. Journal to CSV
            from core.journal import global_journal
            global_journal.log_trade(intent, result)
            
            # 7. Update State (Optimistically increment trades today)
            state_engine.update_pnl(0.0) # Just to increment trade count, PnL update comes from callbacks in real system
            
            return result

        except Exception as e:
            logger.audit(LogCategory.EXECUTION, f"EXECUTION CRITICAL FAILURE: {e}", signal_id=signal.signal_id)
            # FAIL CLOSED: Try to cancel everything just in case
            try:
                self.broker.cancel_all()
            except:
                pass
                
            # TRIGGER KILL SWITCH?
            # Depending on severity. For now, we log critical.
            return False

# Global Singleton
executor = ExecutionEngine()
