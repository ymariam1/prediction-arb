#!/usr/bin/env python3
"""
Script to create mock order book data for the second market in our test pair
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


async def create_second_mock_orderbook():
    """Create mock order book data for the second market in our test pair."""
    print("📊 Creating mock order book data for second market...")
    
    db = next(get_db())
    
    try:
        # Get the second market from our test pair
        second_market = db.query(CanonicalMarket).filter(
            CanonicalMarket.canonical_id == 'kalshi_KXSPOTIFYGLOBALD-25SEP05-ITH_d41d8cd9'
        ).first()
        
        if not second_market:
            print("❌ Second market not found")
            return
        
        print(f"Creating order book for: {second_market.canonical_id}")
        
        # Create mock bid/ask data with different prices to create arbitrage opportunity
        mock_data = [
            # Bids (buy orders) - higher prices than first market
            {"side": "bid", "level": 1, "price": 0.48, "size": 800},
            {"side": "bid", "level": 2, "price": 0.47, "size": 1200},
            {"side": "bid", "level": 3, "price": 0.46, "size": 1000},
            
            # Asks (sell orders) - lower prices than first market
            {"side": "ask", "level": 1, "price": 0.49, "size": 900},
            {"side": "ask", "level": 2, "price": 0.50, "size": 1100},
            {"side": "ask", "level": 3, "price": 0.51, "size": 700},
        ]
        
        for data in mock_data:
            book_level = BookLevels(
                venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c",  # Kalshi venue ID
                market_id=second_market.canonical_id,  # Use canonical ID
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=datetime.now()
            )
            db.add(book_level)
        
        db.commit()
        print(f"✅ Created {len(mock_data)} mock order book levels for second market")
        
        # Verify the data was saved
        count = db.query(BookLevels).filter(BookLevels.market_id == second_market.canonical_id).count()
        print(f"📊 Total book levels for second market: {count}")
        
        return second_market
        
    except Exception as e:
        print(f"❌ Error creating mock order book: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_second_mock_orderbook())
