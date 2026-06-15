# NEXA Institutional Demo Guide

**Target Audience:** Founders, VCs, Chief Risk Officers (CROs), LPs.
**Objective:** Demonstrate the complete lifecycle of capital flow—from client deposit to quantitative research, autonomous trading, AI risk protection, and macro-treasury yield generation.

---

## The Setup (Pre-Demo)
1. Ensure Docker is running via `docker-compose -f docker-compose.prod.yml up -d`.
2. Log into the platform as an **Admin** (to ensure access to all workspaces).
3. Ensure you have no currently assigned strategies running to keep the demo clean.

---

## Step 1: The Product Marketplace & Capital Onboarding
*   **Navigate to:** `Lionex Funds` (`/funds`)
*   **The Pitch:** *"NEXA abstracts complex quantitative mathematics into branded, digestible institutional products. Clients don't buy algorithms; they buy outcomes."*
*   **Action:** 
    1. Highlight the **Lion Alpha Fund** and its 40%+ APY target.
    2. Click **Allocate Capital**.
    3. In the modal, input `$100,000` and click Confirm.
    4. Take note of the dynamically generated Portfolio ID (e.g., `PORT-9921`).
*   **The Transition:** *"We now have $100k of live paper capital bound by strict Alpha Mandate constraints. Let's build the quantitative engine to trade it."*

---

## Step 2: Quantitative Research (Backtesting)
*   **Navigate to:** `Strategy Engine` (`/backtest`)
*   **The Pitch:** *"Our Operators need to validate market theories before risking client capital. This vectorized engine simulates trades against historical TimescaleDB tick data, instantly calculating institutional metrics."*
*   **Action:**
    1. Select `BTC/USDT`, Timeframe `1d`, Strategy `Mean Reversion (RSI)`.
    2. Enter Fast RSI `14`, Overbought `70`, Oversold `30`.
    3. Click **Execute Simulation**.
    4. Show the investor the **Sharpe Ratio**, the **Net Return**, the **Interactive Equity Curve**, and the **Trade History** log at the bottom.
*   **The Transition:** *"This algorithm is highly profitable. We want to deploy it to production."*

---

## Step 3: The Strategy Registry & Assignment
*   **Action (Still on Backtest Page):** Click **Save Strategy**. Name it `BTC_RSI_OPTIMAL`.
*   **Navigate to:** `Strategy Registry` (`/strategies`)
*   **The Pitch:** *"Instead of chaotic scripts, strategies are saved as JSON-parameterized models in our secure registry for Risk Management review."*
*   **Action:**
    1. Find `BTC_RSI_OPTIMAL`. Note its status is currently `Pending Review`.
    2. Click **Assign to Portfolio**.
    3. Select the Portfolio ID you created in Step 1 (`PORT-9921`).
    4. Point out that the status flips to **Active** and is officially assigned to the portfolio.
*   **The Transition:** *"The 'Ghost Operator' background engine is now running. While we wait for it to trade, let me show you how we protect that capital from market crashes."*

---

## Step 4: AI Sentiment & The Risk Gatekeeper
*   **Navigate to:** `Intelligence Hub` (`/intelligence`)
*   **The Pitch:** *"Algorithms are blind to the real world. If the SEC sues a major exchange, an RSI indicator doesn't care—it will still trigger a Buy signal. We solve this with Alternative Data."*
*   **Action:**
    1. Show the Live News Feed and the AI Sentiment Classifications.
    2. Explain the **Market Sensitivity Score**.
    3. Explain the **NEXA Risk Engine**: *"If the Ghost Operator attempts to execute a trade for our new portfolio, the Risk Engine intercepts it. If the Market Sensitivity Score is Extremely Bearish, the AI overrides the quantitative math and blocks the trade to protect capital."*

---

## Step 5: Proving Autonomous Execution
*   **Navigate to:** `Audit Trail` (`/audit`)
*   **The Pitch:** *"Let's see what our Ghost Operator has been doing."*
*   **Action:**
    1. Filter the logs (or just look at the top rows).
    2. You will see `AUTONOMOUS_TRADE_EXECUTED` entries logged by the system while you were doing the rest of the demo. 
    3. Navigate to **Portfolios** (`/portfolios`), click on `PORT-9921`, and show the live trades sitting in the ledger.
*   **The Transition:** *"The capital is trading itself safely. Now, how does the platform make money?"*

---

## Step 6: Macro-Economics & Corporate Treasury
*   **Navigate to:** `Ecosystem Treasury` (`/treasury`)
*   **The Pitch:** *"As client portfolios generate profit, our automated yield-sweeper script skims a 10% performance fee entirely statelessly, dropping it into our corporate Treasury."*
*   **Action:**
    1. Point out the `YIELD` pool.
    2. Click **Sweep Yield**.
    3. Show the alert confirming profits were successfully transferred.
    4. Show the immutable **Treasury Ledger** logging the transfer.

---

## Step 7: The God-Mode View (The Closer)
*   **Navigate to:** `Executive Summary` (`/executive`)
*   **The Pitch:** *"As a Founder, you don't need to look at individual trades. You need to see the entire macro-platform in one glance."*
*   **Action:**
    1. Show **Platform AUM** (Client Capital).
    2. Show **Corporate Treasury NAV** (Your Foundation).
    3. Show **Trades Executed Today** and **Risk Rejections** (Proving the engines are alive).
    4. Finally, point to **LNX Index NAV**. *"LNX is an internal ecosystem index whose NAV is derived from our platform treasury accounting metrics. It reflects the pure performance and growth of our institutional framework."*

**[End of Demo]**