#!/usr/bin/env python3
"""
Script to create mock order book data for testing the arbitrage engine
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.book_levels import BookLevels
from app.models.canonical_market import CanonicalMarket


async def create_mock_orderbook():
    """Create mock order book data for testing."""
    print("📊 Creating mock order book data...")
    
    db = next(get_db())
    
    try:
        # Get a Kalshi market
        kalshi_market = db.query(CanonicalMarket).join(
            CanonicalMarket.rules_text
        ).filter(
            CanonicalMarket.rules_text.has(venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c")
        ).first()
        
        if not kalshi_market:
            print("❌ No Kalshi market found")
            return
        
        print(f"Creating order book for: {kalshi_market.canonical_id}")
        
        # Create mock bid/ask data
        mock_data = [
            # Bids (buy orders)
            {"side": "bid", "level": 1, "price": 0.45, "size": 1000},
            {"side": "bid", "level": 2, "price": 0.44, "size": 2000},
            {"side": "bid", "level": 3, "price": 0.43, "size": 1500},
            
            # Asks (sell orders)
            {"side": "ask", "level": 1, "price": 0.46, "size": 1200},
            {"side": "ask", "level": 2, "price": 0.47, "size": 1800},
            {"side": "ask", "level": 3, "price": 0.48, "size": 900},
        ]
        
        for data in mock_data:
            book_level = BookLevels(
                venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c",  # Kalshi venue ID
                market_id=kalshi_market.id,
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=datetime.now()
            )
            db.add(book_level)
        
        db.commit()
        print(f"✅ Created {len(mock_data)} mock order book levels")
        
        # Verify the data was saved
        count = db.query(BookLevels).filter(BookLevels.market_id == kalshi_market.id).count()
        print(f"📊 Total book levels for this market: {count}")
        
        return kalshi_market
        
    except Exception as e:
        print(f"❌ Error creating mock order book: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_mock_orderbook())
