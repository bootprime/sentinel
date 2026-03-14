from pydantic import BaseModel
from core.contract import SignalPayload

class ExecutionIntent(BaseModel):
    signal: SignalPayload
    quantity: int
    broker_name: str
    timestamp: float
