import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.domain import MarketNewsArticle, NLPSentiment, MarketSensitivityScore, EconomicEvent

logger = logging.getLogger("nexa.nlp_service")

BULLISH_WORDS = {"surge", "rally", "soar", "jump", "climb", "high", "adopt", "launch", "approve", "buy", "up", "bull", "gain", "rise", "boost"}
BEARISH_WORDS = {"crash", "plunge", "tumble", "drop", "fall", "low", "ban", "hack", "reject", "sell", "down", "bear", "loss", "sec", "slump", "recession"}

ASSET_MAPPING = {
    "BTC/USDT": {"bitcoin", "btc"},
    "ETH/USDT": {"ethereum", "eth"},
    "SOL/USDT": {"solana", "sol"},
    "XAUUSD": {"gold", "xau", "bullion", "precious metal"},
    "XAGUSD": {"silver", "xag"},
    "EURUSD": {"euro", "eurusd", "ecb", "european central bank"},
    "GBPUSD": {"pound", "gbp", "sterling", "bank of england"},
    "USDJPY": {"yen", "jpy", "boj", "bank of japan"},
    "WTIUSD": {"oil", "wti", "crude", "opec", "energy"},
    "TLT": {"tlt", "treasury bond", "long-term treasury", "bond yield"},
    "IEF": {"ief", "treasury", "intermediate bond"},
    "SHY": {"shy", "short-term treasury", "t-bill"},
    "HYG": {"hyg", "high yield", "junk bond", "corporate bond"},
    "TIP": {"tip", "inflation protected", "tips"},
    "XLK": {"xlk", "technology sector", "tech etf"},
    "XLF": {"xlf", "financial sector", "bank stocks"},
    "XLE": {"xle", "energy sector"},
    "VXX": {"vxx", "vix", "volatility", "fear index"},
    "UVXY": {"uvxy", "volatility", "vix"},
    "DBC": {"dbc", "commodity index", "commodities"},
    "GSG": {"gsg", "commodity", "gsci"},
    "GLOBAL_RISK": {"recession", "crisis", "war", "default", "inflation", "rate hike", "geopolitical", "fed", "central bank"},
}


def analyze_text_sentiment(text: str) -> float:
    if not text:
        return 0.0
    words = set(re.findall(r'\b\w+\b', text.lower()))
    bull_count = len(words.intersection(BULLISH_WORDS))
    bear_count = len(words.intersection(BEARISH_WORDS))
    total_sentiment_words = bull_count + bear_count
    if total_sentiment_words == 0:
        return 0.0
    score = (bull_count - bear_count) / total_sentiment_words
    return round(score, 2)


def identify_assets(text: str) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    found_assets = []
    for symbol, keywords in ASSET_MAPPING.items():
        if any(keyword in text_lower for keyword in keywords):
            found_assets.append(symbol)
    return found_assets


def _score_economic_events(db: Session):
    """Score unprocessed economic events and emit GLOBAL_RISK sensitivity."""
    unprocessed = (
        db.query(EconomicEvent)
        .outerjoin(
            NLPSentiment,
            (NLPSentiment.reference_id == EconomicEvent.id) & (NLPSentiment.reference_type == "ECONOMIC_EVENT"),
        )
        .filter(NLPSentiment.pk_id.is_(None))
        .limit(50)
        .all()
    )
    global_scores = []
    for event in unprocessed:
        impact = (event.impact or "").upper()
        impact_weight = {"HIGH": -0.6, "MEDIUM": -0.2, "LOW": 0.0}.get(impact, -0.1)
        text = f"{event.event_name} {event.country} {impact}"
        score = analyze_text_sentiment(text) + impact_weight
        score = max(-1.0, min(1.0, round(score, 2)))
        label = "NEUTRAL"
        if score > 0.2:
            label = "BULLISH"
        elif score < -0.2:
            label = "BEARISH"
        db.add(NLPSentiment(
            reference_id=event.id,
            reference_type="ECONOMIC_EVENT",
            sentiment_score=score,
            sentiment_label=label,
            model_version="nexa-heuristic-v1",
        ))
        global_scores.append(score)
    if global_scores:
        avg = sum(global_scores) / len(global_scores)
        db.add(MarketSensitivityScore(
            symbol="GLOBAL_RISK",
            score=round(avg, 2),
            contributing_factors={
                "source": "ECONOMIC_EVENTS",
                "coverage": "DIRECT",
                "data_provenance": "NEWS_AGGREGATE",
                "event_count": len(global_scores),
            },
        ))


def run_nlp_analysis():
    db = SessionLocal()
    try:
        analyzed_ids = db.query(NLPSentiment.reference_id).filter(NLPSentiment.reference_type == 'NEWS').subquery()
        unprocessed_articles = db.query(MarketNewsArticle).filter(MarketNewsArticle.id.notin_(analyzed_ids)).all()

        if unprocessed_articles:
            logger.info(f"Running NLP Sentiment Analysis on {len(unprocessed_articles)} new articles...")
            asset_sentiment_deltas = {sym: [] for sym in ASSET_MAPPING.keys()}

            for article in unprocessed_articles:
                full_text = f"{article.title} {article.content or ''}"
                score = analyze_text_sentiment(full_text)
                label = "NEUTRAL"
                if score > 0.2:
                    label = "BULLISH"
                elif score < -0.2:
                    label = "BEARISH"
                db.add(NLPSentiment(
                    reference_id=article.id,
                    reference_type='NEWS',
                    sentiment_score=score,
                    sentiment_label=label,
                    model_version='nexa-heuristic-v1',
                ))
                for sym in identify_assets(full_text):
                    asset_sentiment_deltas[sym].append(score)

            for symbol, scores in asset_sentiment_deltas.items():
                if not scores:
                    continue
                avg_score = sum(scores) / len(scores)
                db.add(MarketSensitivityScore(
                    symbol=symbol,
                    score=round(avg_score, 2),
                    contributing_factors={
                        "source": "NEWS_AGGREGATE",
                        "coverage": "DIRECT",
                        "data_provenance": "NEWS_AGGREGATE",
                        "article_count": len(scores),
                    },
                ))

        _score_economic_events(db)
        db.commit()
    except Exception as e:
        logger.error(f"NLP analysis failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
