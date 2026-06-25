"""Global market intelligence: multi-source news ingestion + dashboard payload."""
import logging
import urllib.request
import xml.etree.ElementTree as ET
import email.utils
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain
from app.engines.macro_intelligence import MacroIntelligenceEngine
from app.engines.regime_engine import RegimeEngine

logger = logging.getLogger("nexa.market_intelligence")

# RSS feeds: (source, url, region, asset_classes)
NEWS_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "US", ["CRYPTO"]),
    ("Investing.com FX", "https://www.investing.com/rss/news_285.rss", "GLOBAL", ["FX"]),
    ("Investing.com Commodities", "https://www.investing.com/rss/news_301.rss", "GLOBAL", ["METAL", "ENERGY"]),
]


def _fetch_rss(url: str, user_agent: str = "Lionex-Intelligence/1.0") -> Optional[ET.Element]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=15) as response:
            return ET.fromstring(response.read())
    except Exception as e:
        logger.warning("RSS feed unavailable %s: %s", url, e)
        return None


def ingest_news_feeds(db: Session) -> int:
    """Pull multi-region feeds; degrade gracefully when a source is down."""
    new_count = 0
    for source, url, region, asset_classes in NEWS_FEEDS:
        root = _fetch_rss(url)
        if root is None:
            continue
        for item in root.findall("./channel/item"):
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            title = title_el.text.strip()
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            link = link_el.text if link_el is not None else None
            description = desc_el.text if desc_el is not None else ""
            pub_date = datetime.utcnow()
            if pub_el is not None and pub_el.text:
                try:
                    pub_date = datetime(*email.utils.parsedate(pub_el.text)[:6])
                except Exception:
                    pass
            exists = db.query(domain.MarketNewsArticle).filter(domain.MarketNewsArticle.title == title).first()
            if exists:
                continue
            db.add(domain.MarketNewsArticle(
                id=f"news_{uuid.uuid4().hex[:12]}",
                title=title,
                source=source,
                url=link,
                content=description,
                published_at=pub_date,
                region=region,
                asset_classes=asset_classes,
            ))
            new_count += 1
    if new_count:
        db.commit()
    return new_count


class MarketIntelligenceService:
    def __init__(self, db: Session):
        self.db = db

    def dashboard(self) -> Dict[str, Any]:
        """Aggregate global state, regimes, asset registry pulse, and recent news."""
        macro = MacroIntelligenceEngine(self.db)
        global_state = macro.latest() or macro.compute(store=False)
        regimes = (
            self.db.query(domain.MarketRegime)
            .order_by(domain.MarketRegime.detected_at.desc())
            .limit(15)
            .all()
        )
        assets = self.db.query(domain.Asset).filter(domain.Asset.is_active == True).order_by(domain.Asset.symbol).all()
        news = (
            self.db.query(domain.MarketNewsArticle)
            .order_by(domain.MarketNewsArticle.published_at.desc())
            .limit(20)
            .all()
        )
        global_risk = self.db.query(domain.MarketSensitivityScore).filter(
            domain.MarketSensitivityScore.symbol == "GLOBAL_RISK"
        ).order_by(domain.MarketSensitivityScore.timestamp.desc()).first()

        return {
            "global_state": {
                "global_risk_score": global_state.global_risk_score,
                "market_regime": global_state.market_regime,
                "risk_on_off": global_state.risk_on_off,
                "asset_ranking": global_state.asset_ranking,
                "computed_at": global_state.computed_at.isoformat() if global_state.computed_at else None,
            },
            "regimes": [
                {"scope": r.scope, "regime": r.regime, "confidence": r.confidence, "detected_at": r.detected_at.isoformat()}
                for r in regimes
            ],
            "asset_pulse": [
                {"symbol": a.symbol, "display_name": a.display_name, "asset_class": a.asset_class}
                for a in assets
            ],
            "global_risk_sentiment": global_risk.score if global_risk else 0.0,
            "news": [
                {
                    "id": n.id,
                    "title": n.title,
                    "source": n.source,
                    "url": n.url,
                    "published_at": n.published_at.isoformat(),
                    "region": getattr(n, "region", None),
                    "asset_classes": getattr(n, "asset_classes", None),
                }
                for n in news
            ],
        }


def run_market_intelligence_ingestion():
    db = SessionLocal()
    try:
        count = ingest_news_feeds(db)
        if count:
            logger.info("Market intelligence ingested %d articles.", count)
    except Exception as e:
        logger.error("Market intelligence ingestion failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
