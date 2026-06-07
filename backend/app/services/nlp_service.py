import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.domain import MarketNewsArticle, NLPSentiment, MarketSensitivityScore

logger = logging.getLogger("nexa.nlp_service")

# --- MVP Keyword-Based Sentiment Model ---
# In a V2, replace this dictionary approach with HuggingFace/FinBERT
BULLISH_WORDS = {"surge", "rally", "soar", "jump", "climb", "high", "adopt", "launch", "approve", "buy", "up", "bull", "gain"}
BEARISH_WORDS = {"crash", "plunge", "tumble", "drop", "fall", "low", "ban", "hack", "reject", "sell", "down", "bear", "loss", "sec"}

ASSET_MAPPING = {
    "BTC/USDT": {"bitcoin", "btc"},
    "ETH/USDT": {"ethereum", "eth"},
    "SOL/USDT": {"solana", "sol"}
}

def analyze_text_sentiment(text: str) -> float:
    """Calculates a sentiment score between -1.0 and 1.0 based on keyword frequency."""
    if not text:
        return 0.0
    
    words = set(re.findall(r'\b\w+\b', text.lower()))
    bull_count = len(words.intersection(BULLISH_WORDS))
    bear_count = len(words.intersection(BEARISH_WORDS))
    
    total_sentiment_words = bull_count + bear_count
    if total_sentiment_words == 0:
        return 0.0
        
    # Calculate raw score
    score = (bull_count - bear_count) / total_sentiment_words
    return round(score, 2)

def identify_assets(text: str) -> list[str]:
    """Identifies which assets a news article is talking about."""
    if not text:
        return []
        
    text_lower = text.lower()
    found_assets = []
    for symbol, keywords in ASSET_MAPPING.items():
        if any(keyword in text_lower for keyword in keywords):
            found_assets.append(symbol)
            
    return found_assets

def run_nlp_analysis():
    """Scans for unanalyzed news, runs NLP scoring, and updates Asset Sensitivity."""
    db = SessionLocal()
    try:
        # 1. Find articles that haven't been analyzed yet
        analyzed_ids = db.query(NLPSentiment.reference_id).filter(NLPSentiment.reference_type == 'NEWS').subquery()
        unprocessed_articles = db.query(MarketNewsArticle).filter(MarketNewsArticle.id.notin_(analyzed_ids)).all()
        
        if not unprocessed_articles:
            return
            
        logger.info(f"Running NLP Sentiment Analysis on {len(unprocessed_articles)} new articles...")
        
        asset_sentiment_deltas = {sym: [] for sym in ASSET_MAPPING.keys()}
        
        for article in unprocessed_articles:
            # Analyze full text (title + content)
            full_text = f"{article.title} {article.content or ''}"
            score = analyze_text_sentiment(full_text)
            
            label = "NEUTRAL"
            if score > 0.2: label = "BULLISH"
            elif score < -0.2: label = "BEARISH"
            
            # Save the NLP Result
            sentiment_entry = NLPSentiment(
                reference_id=article.id,
                reference_type='NEWS',
                sentiment_score=score,
                sentiment_label=label,
                model_version='nexa-heuristic-v1'
            )
            db.add(sentiment_entry)
            
            # Map to specific assets
            mentioned_assets = identify_assets(full_text)
            for sym in mentioned_assets:
                asset_sentiment_deltas[sym].append(score)
                
        # 2. Update the Global Market Sensitivity Scores
        for symbol, scores in asset_sentiment_deltas.items():
            if not scores:
                continue
                
            avg_score = sum(scores) / len(scores)
            
            # Create a new sensitivity snapshot
            sensitivity = MarketSensitivityScore(
                symbol=symbol,
                score=round(avg_score, 2),
                contributing_factors={"article_count": len(scores), "latest_run_avg": round(avg_score, 2)}
            )
            db.add(sensitivity)
            logger.info(f"Updated Market Sensitivity for {symbol}: {sensitivity.score}")
            
        db.commit()
        logger.info("NLP Sentiment Analysis complete.")
        
    except Exception as e:
        logger.error(f"Error during NLP processing: {e}")
        db.rollback()
    finally:
        db.close()