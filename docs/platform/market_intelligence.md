# Market Intelligence

News, sentiment, and macro context feeding the risk and allocation layers.

---

## Data Sources

| Source | Cadence | Output |
|--------|---------|--------|
| RSS (CoinDesk, Investing.com) | Hourly scrape + 2h ingestion | `market_news_articles` |
| NLP analyzer | Every 10 min | `nlp_sentiments`, `market_sensitivity_scores` |
| Economic calendar | Every 6 hours | `economic_events` |
| Market bars | Hourly | Regime + macro inputs |

---

## NLP Scoring

Heuristic `nexa-heuristic-v1`: bullish/bearish keyword counts → score −1 to +1.

Coverage labels on UI:

| Coverage | Meaning |
|----------|---------|
| DIRECT | Article mentions asset |
| ASSET_CLASS_PROXY | Proxy peer asset |
| (none) | **NO DATA** — not shown as neutral 50 |

---

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/intelligence/news` | Headlines |
| `GET /api/intelligence/sentiment` | Per-symbol scores |
| `GET /api/intelligence/events` | Economic calendar |
| `GET /api/market-intelligence/dashboard` | Unified dashboard |

---

## UI Routes

| Route | Content |
|-------|---------|
| `/intelligence` | Intelligence Hub — news, pulse, events |
| `/market-intelligence` | Asset pulse + regional news |
| Dashboard widget | Global risk, regime, top ranked assets |

---

## Global Risk Sentiment

`GLOBAL_RISK` row in `market_sensitivity_scores` aggregates economic event impact + news text.

Feeds macro intelligence sentiment component (20% of dashboard risk score).

See [Risk Engine](./risk_engine.md).
