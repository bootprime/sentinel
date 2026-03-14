# 🧠 Sentinel (v1.0)
> Production-Grade Intraday Trading System

## 🎯 Goal
A capital-protection-first, mechanical execution system for TradingView strategies.
**Philosophy**: Fail-closed, Zero Discretion, Rigid Contract.

## 🧱 Architecture
**Flow**: `TradingView (Pine)` -> `Browser Extension` -> `FastAPI` -> `Gates` -> `State` -> `Broker`

1. **Pine Script**: Generates a Signal Table (JSON) on the chart.
2. **Extension**: Scrapes the DOM for the JSON, deduplicates, and forwards to `localhost:8001`.
3. **API**: Receives payload, authenticates (Active), and validates.
4. **Phase-7 Gates**: 7 mandatory checks (Freshness, Dedup, Strategy, RR, Structure, Session, State).
5. **Executor**: Checks Global State again, calculates size (Hypercare: 1 qty), and routes to Broker.
6. **Broker**: Executes the trade (currently `NullBroker` for PAPER/SAFE mode).

## 🛡️ Safety Mechanisms (The "Why")
- **Fail-Closed**: Any error in the pipe drops the signal. We never "guessed" or "retried" blindly.
- **Global State**: Persisted in `data/state.json`. If `daily_pnl` hits loss limit -> `DAILY_LOCK`.
- **Deduplication**: In-memory TTL cache prevents double-firing of the same signal ID.
- **Hypercare**: Hardcoded 1 lot limit in `core/executor.py` initially to prevent size errors.

## 🚀 How to Run

### 1. Requirements
Python 3.9+
`pip install -r requirements.txt`

### 2. Start Backend
```bash
python main.py
```
*Server runs on 127.0.0.1:8001. Check console for "Sentinel System Starting Up..."*

### 3. Load Extension
1. Chrome -> Extensions -> Manage Extensions.
2. Enable **Developer Mode**.
3. "Load Unpacked" -> Select `extension/` folder.
4. Verify the badge is **GREEN** (backend connected).

### 4. Open TradingView
1. Add `pine/strategy_A.pine` to your chart.
2. Wait for a signal. The Extension logs "Found New Signal" and forwards it.
3. Check `sentinel.log` for execution details.

## 🧪 Testing
Run the verification suite:
```bash
pytest tests/
```
**RULE**: Do not trade if tests fail.

## 📂 Structure
- `core/`: Brains (Config, State, Gates).
- `broker/`: Arms (Execution adapters).
- `api/`: Mouth (Input interface).
- `extension/`: Eyes (Reading the charts).
