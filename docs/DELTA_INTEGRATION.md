# Delta Exchange Integration Guide

## Overview

Delta Exchange broker adapter has been successfully integrated into Sentinel, providing support for crypto derivatives trading alongside existing Zerodha (Kite) and Dhan brokers.

---

## Features

### ✅ Implemented

- **HMAC SHA256 Authentication** - Secure API key-based authentication
- **Order Management** - Market and stop-loss order placement
- **Position Tracking** - Real-time position monitoring
- **LTP Fetching** - Last traded price retrieval
- **Order Status Tracking** - Complete, partial, and pending order states
- **Emergency Flatten** - Quick position exit capability
- **Testnet Support** - Safe testing environment before live trading

### 🔄 Architecture

```
Sentinel Signal
    ↓
Gate System (Validation)
    ↓
Option Engine (Strike Selection)
    ↓
Risk Engine (SL/TP Calculation)
    ↓
Execution Engine
    ↓
Broker Manager → Delta Broker → Delta Exchange API
```

---

## Configuration

### 1. Update `credentials.json`

Add Delta Exchange credentials to `data/credentials.json`:

```json
{
  "MODE": "PAPER",
  "active_broker": "DELTA",
  "DELTA": {
    "api_key": "YOUR_DELTA_API_KEY",
    "api_secret": "YOUR_DELTA_API_SECRET",
    "testnet": true
  }
}
```

### 2. Obtain API Credentials

**Testnet (Recommended for Testing):**
1. Visit https://testnet.delta.exchange
2. Create account
3. Navigate to Settings → API Keys
4. Generate new API key pair
5. Copy `api_key` and `api_secret`

**Production:**
1. Visit https://www.delta.exchange
2. Complete KYC verification
3. Navigate to Settings → API Keys
4. Generate new API key pair with trading permissions
5. Copy credentials and set `"testnet": false`

---

## API Key Permissions

Ensure your Delta Exchange API key has the following permissions:

- ✅ **Read** - View account, positions, orders
- ✅ **Trade** - Place and cancel orders
- ❌ **Withdraw** - Not required (keep disabled for security)

---

## Symbol Mapping

Delta Exchange uses product IDs instead of symbol strings. Current mappings:

| Sentinel Symbol | Delta Product ID | Description |
|----------------|------------------|-------------|
| `BTCUSD` | 27 | Bitcoin Perpetual |
| `ETHUSD` | 28 | Ethereum Perpetual |

### Adding New Symbols

Edit `core/broker/delta.py` → `_get_product_id()` method:

```python
symbol_map = {
    "BTCUSD": 27,
    "ETHUSD": 28,
    "SOLUSD": 139,  # Add new mappings here
}
```

To find product IDs:
```bash
curl https://api.delta.exchange/v2/products
```

---

## Order Types

### Market Order

```python
order_params = {
    "symbol": "BTCUSD",
    "qty": 10,
    "type": "BUY",
    "order_type": "MARKET"
}
```

### Stop Loss Order

```python
order_params = {
    "symbol": "BTCUSD",
    "qty": 10,
    "type": "SELL",
    "order_type": "SL",
    "trigger_price": 50000.0
}
```

---

## Testing

### Unit Tests

Run Delta broker tests:

```bash
pytest tests/unit/test_delta_broker.py -v
```

Expected output:
```
test_init_production PASSED
test_init_testnet PASSED
test_generate_signature PASSED
test_authenticate_success PASSED
test_place_order_market PASSED
test_get_order_status_complete PASSED
...
```

### Integration Testing

1. **Set testnet mode:**
   ```json
   "DELTA": {
     "api_key": "testnet_key",
     "api_secret": "testnet_secret",
     "testnet": true
   }
   ```

2. **Start Sentinel:**
   ```bash
   python main.py
   ```

3. **Verify connection:**
   Look for log:
   ```
   Delta Connected: 12345 (test@example.com)
   ```

4. **Send test signal:**
   Use TradingView webhook or manual API call to `/signal`

---

## Differences from Kite/Dhan

| Feature | Kite/Dhan | Delta Exchange |
|---------|-----------|----------------|
| **Authentication** | Access token (24h expiry) | API key (no expiry) |
| **Symbol Format** | String (e.g., "NIFTY24500CE") | Product ID (e.g., 27) |
| **Market** | Indian equity derivatives | Crypto derivatives |
| **Order Types** | MARKET, SL, SL-M | market_order, stop_market_order |
| **Exchange** | NSE/NFO | Delta Exchange |
| **Testnet** | Not available | Available |

---

## Error Handling

### Common Errors

**1. Invalid API Key**
```
Error: Delta Authentication Failed: Missing API Key or Secret
```
**Solution:** Verify credentials in `credentials.json`

**2. Invalid Product ID**
```
Error: Invalid symbol: UNKNOWN
```
**Solution:** Add symbol mapping in `_get_product_id()`

**3. Insufficient Balance**
```
Error: insufficient_margin
```
**Solution:** Add funds to Delta Exchange account

**4. Rate Limit Exceeded**
```
Error: rate_limit_exceeded
```
**Solution:** Reduce order frequency or upgrade API tier

---

## Security Best Practices

1. **Never commit credentials** - Add `credentials.json` to `.gitignore`
2. **Use testnet first** - Always test with testnet before production
3. **Minimal permissions** - Only enable Read + Trade permissions
4. **IP whitelisting** - Configure allowed IPs in Delta settings
5. **Rotate keys regularly** - Generate new API keys every 90 days

---

## Token Lifecycle

Unlike Kite/Dhan, Delta API keys don't expire automatically:

- **Lifetime:** Indefinite (until manually revoked)
- **Refresh:** Not required
- **Monitoring:** Token manager tracks for 365 days as placeholder
- **Rotation:** Manual via Delta Exchange dashboard

---

## Production Checklist

Before going live with Delta Exchange:

- [ ] Complete KYC verification on Delta Exchange
- [ ] Test all order types on testnet
- [ ] Verify symbol mappings for your trading instruments
- [ ] Set up IP whitelisting
- [ ] Configure position size limits in Sentinel
- [ ] Test emergency flatten functionality
- [ ] Enable WebSocket notifications
- [ ] Set `"testnet": false` in credentials
- [ ] Monitor first few trades closely

---

## API Rate Limits

Delta Exchange rate limits (as of 2024):

| Tier | Requests/Second | Requests/Minute |
|------|-----------------|-----------------|
| Free | 10 | 300 |
| Pro | 30 | 1000 |
| Enterprise | Custom | Custom |

Sentinel's execution frequency is well within these limits for normal trading.

---

## Troubleshooting

### Connection Issues

```bash
# Test API connectivity
curl -X GET "https://testnet-api.delta.exchange/v2/products" \
  -H "api-key: YOUR_KEY" \
  -H "signature: GENERATED_SIGNATURE" \
  -H "timestamp: CURRENT_TIMESTAMP"
```

### Debug Logging

Enable debug logs in `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### WebSocket Monitoring

Check real-time updates in browser console:

```javascript
ws.on('fill', (data) => {
  console.log('Delta fill:', data);
});
```

---

## Next Steps

1. **Symbol Mapping Service** - Dynamic product ID resolution
2. **WebSocket Market Data** - Real-time price streaming
3. **Advanced Order Types** - Limit orders, iceberg orders
4. **Multi-leg Strategies** - Spreads and combinations
5. **Portfolio Margin** - Cross-margin support

---

## Support

- **Delta Exchange Docs:** https://docs.delta.exchange/
- **API Status:** https://status.delta.exchange/
- **Support:** support@delta.exchange
- **Sentinel Issues:** Create issue in project repository

---

## Example Workflow

```bash
# 1. Configure credentials
vim data/credentials.json

# 2. Start Sentinel
python main.py

# 3. Check logs
tail -f sentinel_boot.log

# 4. Send test signal (via TradingView or API)
curl -X POST http://localhost:8001/signal \
  -H "Content-Type: application/json" \
  -d @test_signal.json

# 5. Monitor execution
# Check dashboard at http://localhost:5173

# 6. Verify on Delta Exchange
# Login to testnet.delta.exchange → Orders
```

---

**Status:** ✅ Delta Exchange integration complete and ready for testing
