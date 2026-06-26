# NEXA Platform: Formal Demo Scripts

This document provides four distinct, persona-driven demonstration scripts designed to showcase the platform's core value propositions to different stakeholders.

See also: [Validation](../platform/validation.md) · [DEMO Script D](#demo-script-d-institutional-validation--analytics) for the validation demo.

---

## Demo Script A: The Client Experience

*   **Objective:** Demonstrate a seamless, intuitive, and transparent client onboarding and portfolio tracking experience.
*   **Persona:** Logged in as a **Client**.

### Click-Path & Pitch Points

1.  **Navigate to `/funds` (Lionex Funds):**
    *   **Pitch:** *"Our platform abstracts complex algorithms into simple, branded investment products. As a client, I can easily see the risk/return profile of each fund without needing to understand the underlying code."*

2.  **Click "Allocate Capital" on the Lion Alpha Fund:**
    *   **Pitch:** *"I'm looking for aggressive growth, so I'll allocate $100,000 to the high-yield Alpha fund. The process is as simple as a few clicks."*

3.  **Confirm Allocation in the Modal:**
    *   **Pitch:** *"The system instantly creates and funds a new, segregated portfolio for me, `PORT-XYZ`, which is now ready for the firm's autonomous strategies to manage."*

4.  **Navigate to `/portfolios`:**
    *   **Pitch:** *"I can see my new portfolio here, with its capital ready to be deployed. I have a transparent, real-time view of my equity and performance at all times."*

5.  **Navigate to `/simulator` (Growth Simulator):**
    *   **Pitch:** *"To understand the potential of my investment, I can use the simulator. Based on the Alpha fund's historical algorithmic performance, I can project the potential growth of my $100k deposit over the next 12 months."*

6.  **Navigate to `/lnx` (LNX Ecosystem):**
    *   **Pitch:** *"Finally, I can track the LNX Index. This isn't a speculative token; it's an internal accounting metric that reflects the overall health and performance of the entire platform's treasury, giving me confidence in the ecosystem I've invested in."*

---

## Demo Script B: The Quant & Operator Workflow

*   **Objective:** Prove the end-to-end quantitative research, deployment, and autonomous execution pipeline.
*   **Persona:** Logged in as an **Operator** or **Admin**.

### Click-Path & Pitch Points

1.  **Navigate to `/backtest` (Strategy Engine):**
    *   **Pitch:** *"Our quants don't guess; they validate. Here, we can test a Mean Reversion (RSI) strategy on historical BTC/USDT data from our own TimescaleDB instance."*

2.  **Run Simulation & Review Results:**
    *   **Pitch:** *"The engine provides instant feedback: a Sharpe Ratio of 1.82, a positive net return, and a full trade-by-trade ledger. This strategy meets our criteria for deployment."*

3.  **Click "Save Strategy":**
    *   **Pitch:** *"We'll save this validated model as `BTC_RSI_ALPHA` to our central registry, turning a successful backtest into a deployable asset."*

4.  **Navigate to `/strategies` (Strategy Registry):**
    *   **Pitch:** *"Here is our new strategy, pending review. As a manager, I can now assign it to a live portfolio for autonomous execution."*

5.  **Click "Assign to Portfolio":**
    *   **Action:** Select the client's portfolio (`PORT-XYZ`) and choose the `Binance` exchange from the dropdown.
    *   **Pitch:** *"The strategy is now active and assigned to execute on the Binance Testnet. The 'Ghost Operator' has taken over."*

6.  **Navigate to `/execution-monitor`:**
    *   **Pitch:** *"We can see the live, operational connection to the Binance Testnet, with real-time latency data. In a few moments, we'll see our autonomous trades appear here."*

7.  **Wait 60-120 seconds.**

8.  **Navigate to `/audit` (Audit Trail):**
    *   **Pitch:** *"And here is the proof. The audit log shows an `AUTONOMOUS_TRADE_EXECUTED_VIA_BINANCE` event, logged by the system with a corresponding exchange order ID. The machine is trading, and every action is immutably recorded for compliance."*

---

## Demo Script C: The Risk Manager & Governance Audit

*   **Objective:** Demonstrate the platform's robust, non-negotiable risk controls and its ability to survive adverse market events.
*   **Persona:** Logged in as a **Risk Manager** or **Admin**.

### Click-Path & Pitch Points

1.  **Navigate to `/stress-test` (Risk Validation Suite):**
    *   **Pitch:** *"The most important feature of an institutional platform isn't how much it makes, but how much it *doesn't lose*. This is our validation suite where we prove our safety mechanisms."*

2.  **Run "Leverage Ceiling Violation" Scenario:**
    *   **Pitch:** *"First, let's simulate a rogue algorithm trying to use 13x leverage on a 3x mandate. We run the scenario..."*
    *   **Show Result:** *"...and the Risk Engine instantly intercepts and blocks the trade, logging the exact leverage breach. Capital is protected."*

3.  **Run "AI Extreme News Gatekeeper" Scenario:**
    *   **Pitch:** *"Now, let's simulate a market crash. A quant signal says 'BUY', but our AI has detected extreme fear in the news cycle."*
    *   **Show Result:** *"...the AI Gatekeeper overrides the algorithm and blocks the trade. We prevent the system from buying into a crash, demonstrating intelligent risk aversion."*

4.  **Navigate to `/mandates` (Mandate Contracts):**
    *   **Pitch:** *"Our risk rules aren't suggestions; they are immutable contracts. Let's say we need to de-risk the entire Alpha fund. We'll edit the mandate to reduce max leverage from 3x to 2x."*

5.  **Update Mandate & Show History:**
    *   **Pitch:** *"The system automatically archives the old version and migrates all assigned portfolios to the new, safer parameters. The entire version history is preserved for compliance audits."*

6.  **Navigate to `/execution-health`:**
    *   **Pitch:** *"Finally, we can monitor the real-time health of the entire execution stack. We track order throughput, success rates, and risk rejections per hour, giving us a complete, data-driven governance overview."*

---

## Demo Script D: Institutional Validation & Analytics

*   **Objective:** Demonstrate the 5-stage institutional validation roadmap — rolling metrics, PDF reports, trade explorer, and comparison tools.
*   **Persona:** Logged in as **Risk Manager**, **Operator**, or **Admin**.

### Click-Path & Pitch Points

1.  **Navigate to `/validation`:**
    *   **Pitch:** *"Institutional validation defaults to **Validated Historical** — aggregated backtests on real market bars for all three Lionex funds. This is what we show investors."*
    *   **Show:** Period tabs, KPI grid, equity-based Sharpe and drawdown (~8% CAGR range, ~17–24% max DD on ALL period).

2.  **Toggle Demo Ledger (admin only):**
    *   **Pitch:** *"For internal ops we can switch to the **Demo Ledger** — seeded autonomous paper trades. Never use this column in investor materials."*

3.  **Navigate to `/fund-performance`:**
    *   **Pitch:** *"Fund Performance is always validated historical first. Check **Show demo comparison** to contrast with seeded client portfolio ledgers side-by-side."*

4.  **Open `/portfolios/LNX-ALPHA-VALIDATED` (admin):**
    *   **Pitch:** *"Reference portfolios mirror the best optimization run — equity curve, rebalance log, settlements, and backtest-derived P&L."*

5.  **Download validation PDF (demo mode optional):**
    *   **Action:** Use PDF buttons on `/validation` while in appropriate data source mode.

6.  **Navigate to `/trade-explorer`:**
    *   **Action:** Filter by `trade_source=AUTONOMOUS`, exchange, or strategy name.
    *   **Pitch:** *"Every trade — filled, rejected, or manual — is searchable. Rejections include the exact reason from the risk engine or exchange."*

7.  **Navigate to `/analytics/compare`:**
    *   **Action:** Select 2–3 portfolios or strategies for side-by-side comparison.
    *   **Pitch:** *"Portfolio and strategy comparison tools let risk teams identify outperformers and laggards without exporting to Excel."*

8.  **Navigate to `/strategies`:**
    *   **Pitch:** *"The strategy registry now shows live performance analytics — win rate and PnL per algorithm — updated from real execution data."*

9.  **Navigate to `/audit`:**
    *   **Action:** Search for "AUTONOMOUS" or filter by exchange.
    *   **Pitch:** *"Privileged roles see the full system audit trail with search and date filters — every autonomous execution, risk rejection, and mandate change is immutably logged."*

### Pre-Demo Setup

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm

# Ensure validated runs + reference portfolios exist (admin)
docker compose -f docker-compose.prod.yml exec backend python scripts/run_alpha_optimization.py --phase all

docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
```

Log in as **`admin@google.com`** / `password123` for validated toggles and demo comparison.