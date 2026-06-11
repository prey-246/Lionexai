import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime
import uuid
import logging

# Setup path to allow importing the app module from the scripts directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import MarketNewsArticle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_crypto_news():
    """Scrapes the CoinDesk RSS feed and saves new articles to the DB."""
    url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    db = SessionLocal()
    
    try:
        logger.info(f"Fetching news from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'NEXA-Intelligence-Bot/1.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        new_count = 0
        
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            link = item.find('link').text
            description = item.find('description').text
            pub_date_str = item.find('pubDate').text
            
            # Parse standard RSS RFC-822 date formats
            pub_date = datetime(*email.utils.parsedate(pub_date_str)[:6])
            
            # Check if we already have this article based on exact title to prevent duplicates
            exists = db.query(MarketNewsArticle).filter(MarketNewsArticle.title == title).first()
            if not exists:
                article = MarketNewsArticle(
                    title=title,
                    source="CoinDesk",
                    url=link,
                    content=description,
                    published_at=pub_date
                )
                db.add(article)
                new_count += 1
                
        db.commit()
        logger.info(f"Successfully scraped and saved {new_count} new market articles.")
    except Exception as e:
        logger.error(f"Failed to scrape news: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    scrape_crypto_news()