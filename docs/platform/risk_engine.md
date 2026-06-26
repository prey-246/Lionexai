# Risk Engine

Two complementary risk scores — use the right one for each surface.

---

## Macro Intelligence (Dashboard Widget)

**Service:** `engines/macro_intelligence.py`  
**Storage:** `global_market_state`  
**Update:** Hourly  
**API:** `GET /api/market/global-state`

### Components (weighted 0–100)

| Component | Weight |
|-----------|--------|
| Volatility | 34% |
| Equity drawdown | 22% |
| Sentiment | 20% |
| Economic severity | 12% |
| Safe-haven | 12% |

**Risk posture:** ≥60 RISK_OFF, ≤40 RISK_ON, else NEUTRAL.  
**Regime:** BULL / BEAR / SIDEWAYS / CRISIS (forced if score ≥78).

---

## Global Risk Engine v2 (Institutional)

**Service:** `engines/global_risk_engine.py`  
**Update:** On-demand  
**API:** `GET /api/validated/global-risk`

Starts from macro base, then adjusts for:

- News sentiment (last 20 scores)
- BTC realized vol, gold momentum, EURUSD momentum
- Cross-asset correlation stress
- FRED: VIX, yield curve (when `FRED_API_KEY` set)

Returns `components` dict for explainability. Labels: LOW / BALANCED / MODERATE / ELEVATED.

---

## Mandate Risk

Per-portfolio limits in `mandates` table: max leverage, drawdown, position size, kill switch.

Enforced at trade execution via risk engine checks.

---

## Stress Tests

`/stress-test` — scenario simulation on portfolio (`POST /api/stress-test/{scenario}/run`).

Treasury verification includes MARKET_CRASH_20/40, reserve depletion scenarios.

---

## UI Routes

| Route | Risk content |
|-------|--------------|
| `/risk` | Command center |
| `/mandates` | Mandate CRUD |
| `/stress-test` | Scenario runs |
| Dashboard widget | Macro risk score |

See [AI Pipeline](../architecture/ai_pipeline.md).
