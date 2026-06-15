# NEXA API Schema Reference

This document outlines the strict JSON schemas, parameters, and response objects utilized by the FastAPI backend.

## 1. System & Authentication

### `POST /api/auth/token`
*   **Auth**: Public
*   **Request**: `application/x-www-form-urlencoded` (`username`, `password`)
*   **Response**: 
    ```json
    { "access_token": "eyJhb...", "token_type": "bearer" }
    ```

### `GET /api/users/me`
*   **Auth**: Required
*   **Response**:
    ```json
    { "id": "uuid", "email": "user@nexa.com", "role_tier": "operator", "is_active": true }
    ```

### `GET /api/system/health`
*   **Auth**: Public
*   **Response**:
    ```json
    {
      "status": "online",
      "database": "connected",
      "active_mandates": 3,
      "trades_today": 142,
      "active_users": 8,
      "timestamp": "2024-06-10T12:00:00Z"
    }
    ```

---

## 2. Risk Mandates

### `POST /api/mandates`
*   **Auth**: `admin`, `risk_manager`
*   **Request**:
    ```json
    {
      "id": "ALPHA",
      "name": "Alpha Fund",
      "description": "High yield algorithmic fund.",
      "risk_tier": "High",
      "max_leverage": 3.0,
      "max_drawdown_pct": 20.0,
      "daily_loss_limit_pct": 5.0,
      "max_position_size_pct": 30.0,
      "max_portfolio_exposure_pct": 100.0,
      "max_open_positions": 20,
      "restricted_assets_enabled": false,
      "kill_switch_enabled": true,
      "allowed_assets": ["ALL"]
    }
    ```
*   **Response**: Returns the created mandate with `pk_id` and `version: 1`.

### `PUT /api/mandates/{pk_id}`
*   **Auth**: `admin`, `risk_manager`
*   **Behavior**: Archives the old version, creates a new version (`version + 1`), and automatically migrates all associated portfolios.
*   **Request**: Partial `Mandate` object.

---

## 3. Portfolios & Trading

### `POST /api/portfolios`
*   **Auth**: Required
*   **Request**:
    ```json
    {
      "id": "PORT-84CB",
      "mandate_pk_id": "1",
      "total_equity": 100000.0
    }
    ```

### `POST /api/trading/{portfolio_id}/execute`
*   **Auth**: Required
*   **Behavior**: Passes the request through the `RiskEngine`.
*   **Request**:
    ```json
    {
      "symbol": "BTC/USDT",
      "side": "BUY",
      "size": 1.5,
      "stop_loss": 64000.0
    }
    ```
*   **Response (Success)**: `{ "status": "FILLED", "trade_id": "...", "fill_price": 65000.00 }`
*   **Response (Failure)**: HTTP 403 Forbidden - `{ "detail": "Leverage limit exceeded." }`

---

## 4. Quantitative Strategy Engine

### `POST /api/backtest/run`
*   **Auth**: Required
*   **Request**:
    ```json
    {
      "symbol": "BTC/USDT",
      "timeframe": "1d",
      "strategy": "ma_crossover",
      "initial_capital": 100000,
      "strategy_params": { "fast_ma": 10, "slow_ma": 50 }
    }
    ```
*   **Response**:
    ```json
    {
      "status": "success",
      "symbol": "BTC/USDT",
      "metrics": {
        "final_capital": 112450.75,
        "total_return_pct": 12.45,
        "max_drawdown_pct": 8.25,
        "win_rate_pct": 58.3,
        "sharpe_ratio": 1.82,
        "total_trades_simulated": 47
      },
      "equity_curve": [ { "time": 1700000000, "value": 100000 } ],
      "trades": [ { "timestamp": "...", "side": "BUY", "price": 65000, "pnl": null } ]
    }
    ```

### `POST /api/strategies`
*   **Auth**: `operator`, `risk_manager`, `admin`
*   **Request**:
    ```json
    {
      "id": "MA_OPTIMAL",
      "name": "MA Optimal",
      "description": "...",
      "strategy_type": "ma_crossover",
      "parameters": { "fast_ma": 10, "slow_ma": 50 }
    }
    ```

### `PUT /api/strategies/{id}`
*   **Auth**: `admin`
*   **Behavior**: Used for Portfolio Assignment. Pass `{ "is_active": true, "parameters": { "assigned_portfolio_id": "PORT-123" } }` to trigger the Autonomous Trading Engine.

---

## 5. Treasury Ecosystem

### `POST /api/treasury/sweep`
*   **Auth**: `admin`
*   **Behavior**: Calculates 10% of total historical platform profits minus previously swept amounts, and transfers the delta to the `YIELD` pool.

### `POST /api/treasury/transfer`
*   **Auth**: `admin`
*   **Request**:
    ```json
    {
      "source_pool_id": "RESERVE",
      "target_pool_id": "GROWTH",
      "amount": 50000.0,
      "description": "Ecosystem expansion grant."
    }
    ```

---

## 6. Audit & Compliance

### `GET /api/audit`
*   **Parameters**: `action_type`, `limit`, `offset`
*   **Returns**: Paginated list of immutable event logs with `metadata_json` context.

### `GET /api/reports/{id}/download`
*   **Behavior**: Triggers the `WeasyPrint` rendering engine and returns a raw `application/pdf` Blob.