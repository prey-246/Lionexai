import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid
import sys
import os

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import EconomicEvent

def fetch_and_store_events():
    """
    Fetches the weekly economic calendar from ForexFactory's free XML feed
    and stores the events into the NEXA Intelligence database.
    """
    print("Fetching live macro-economic events...")
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        db = SessionLocal()
        events_added = 0
        
        for item in root.findall('event'):
            title = item.find('title').text if item.find('title') is not None else "Unknown Event"
            country = item.find('country').text if item.find('country') is not None else "Unknown"
            date_str = item.find('date').text
            time_str = item.find('time').text
            impact = item.find('impact').text if item.find('impact') is not None else "Low"
            forecast = item.find('forecast').text if item.find('forecast') is not None else None
            previous = item.find('previous').text if item.find('previous') is not None else None
            
            # Only parse valid times (skip "All Day" or "Tentative")
            if time_str and ":" in time_str:
                dt_string = f"{date_str} {time_str}"
                try:
                    # Format: mm-dd-yyyy h:mma (e.g., 06-07-2024 8:30am)
                    event_time = datetime.strptime(dt_string, "%m-%d-%Y %I:%M%p")
                    
                    # Check if event already exists
                    exists = db.query(EconomicEvent).filter(
                        EconomicEvent.event_name == title,
                        EconomicEvent.timestamp == event_time
                    ).first()
                    
                    if not exists:
                        new_event = EconomicEvent(
                            event_name=title, country=country, impact=impact,
                            forecast_value=forecast, previous_value=previous, timestamp=event_time
                        )
                        db.add(new_event)
                        events_added += 1
                except ValueError:
                    continue
                    
        db.commit()
        db.close()
        print(f"Success! {events_added} new economic events seeded to the database.")
        
    except Exception as e:
        print(f"Failed to fetch economic events: {e}")

if __name__ == "__main__":
    fetch_and_store_events()