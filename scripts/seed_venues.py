#!/usr/bin/env python3
"""
Script to seed the database with venue data.
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db, create_tables
from app.models.venue import Venue


def seed_venues():
    """Seed the database with venue data."""
    # Create tables if they don't exist
    create_tables()
    
    db = next(get_db())
    try:
        # Check if venues already exist
        existing_venues = db.query(Venue).all()
        if existing_venues:
            print("Venues already exist in database:")
            for venue in existing_venues:
                print(f"  - {venue.name}: {venue.display_name}")
            return
        
        # Create venue records
        venues_data = [
            {
                "name": "kalshi",
                "display_name": "Kalshi",
                "api_base_url": "https://trading-api.kalshi.com/v1",
                "is_active": True,
                "venue_type": "prediction_market",
                "description": "Kalshi is a prediction market platform for trading on real-world events."
            },
            {
                "name": "polymarket",
                "display_name": "Polymarket",
                "api_base_url": "https://clob.polymarket.com",
                "is_active": True,
                "venue_type": "prediction_market",
                "description": "Polymarket is a decentralized prediction market platform built on Polygon."
            }
        ]
        
        for venue_data in venues_data:
            venue = Venue(**venue_data)
            db.add(venue)
            print(f"Added venue: {venue.name} - {venue.display_name}")
        
        db.commit()
        print(f"\n✅ Successfully seeded {len(venues_data)} venues")
        
    except Exception as e:
        print(f"❌ Error seeding venues: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding venue data...")
    seed_venues()
    print("Done!")
