from fastapi import APIRouter, HTTPException
from core.config import runtime_settings, save_runtime_config, RuntimeConfig
from core.audit import audit

router = APIRouter(prefix="/config", tags=["Configuration"])

@router.get("/", response_model=RuntimeConfig)
async def get_config():
    """
    Get current runtime configuration (Option & Risk settings).
    """
    return runtime_settings

@router.put("/", response_model=RuntimeConfig)
async def update_config(new_config: RuntimeConfig):
    """
    Update runtime configuration and persist to disk.
    """
    global runtime_settings
    try:
        # Trace Entry
        audit.info(f"SYSTEM: Authority Update Request Received")

        # 1. Targeted Segment Diffing
        changed_sections = []
        
        # Option Diff
        if runtime_settings.option.model_dump() != new_config.option.model_dump():
            o = new_config.option
            audit.info(f"SETUP: Option Strategy Updated - Mode: {o.option_mode}, Step: {o.strike_step}, Offset: {o.strike_offset}")
            changed_sections.append("option")
            
        # Risk Diff
        if runtime_settings.risk.model_dump() != new_config.risk.model_dump():
            audit.info(f"SETUP: Risk Translation Updated - Method: {new_config.risk.mode}")
            changed_sections.append("risk")

        # Discipline Diff (High-Authority)
        if runtime_settings.discipline.model_dump() != new_config.discipline.model_dump():
            d = new_config.discipline
            audit.info(f"ADMIN: Discipline Protocol Overwritten - TradeQty: {d.trade_qty}, MaxTrades: {d.max_trades_per_day}, DailyLoss: {d.max_daily_loss}, DailyTarget: {d.max_daily_profit}")
            changed_sections.append("discipline")

        # 2. Apply updates
        runtime_settings.option = new_config.option
        runtime_settings.risk = new_config.risk
        runtime_settings.discipline = new_config.discipline
        
        # 3. Persistence (Always persist if reached here, ensuring state is synced)
        save_runtime_config(runtime_settings)
        
        if not changed_sections:
            audit.info("SYSTEM: Configuration synced (No changes detected)")

        return runtime_settings
    except Exception as e:
        audit.error(f"SYSTEM: Config Auth Failure - {e}")
        raise HTTPException(status_code=500, detail=str(e))
