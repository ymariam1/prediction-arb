#!/usr/bin/env python3
"""
Script to create a test pair between two Kalshi markets for arbitrage testing
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.pairs import Pairs
from app.models.canonical_market import CanonicalMarket


async def create_kalshi_test_pair():
    """Create a test pair between two Kalshi markets."""
    print("🔗 Creating a test pair between two Kalshi markets...")
    
    db = next(get_db())
    
    try:
        # Get two Kalshi markets
        kalshi_markets = db.query(CanonicalMarket).join(
            CanonicalMarket.rules_text
        ).filter(
            CanonicalMarket.rules_text.has(venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c")
        ).limit(2).all()
        
        if len(kalshi_markets) < 2:
            print("❌ Need at least two Kalshi markets")
            return
        
        market_a = kalshi_markets[0]
        market_b = kalshi_markets[1]
        
        print(f"Market A: {market_a.canonical_id}")
        print(f"Market B: {market_b.canonical_id}")
        print(f"Market A question: {market_a.question_text[:100]}...")
        print(f"Market B question: {market_b.question_text[:100]}...")
        
        # Create a test pair with manual values
        test_pair = Pairs(
            market_a_id=market_a.id,
            market_b_id=market_b.id,
            equivalence_score=0.8,  # High score for testing
            conflict_list=["Test pair for arbitrage engine testing"],
            hard_ok=True,
            confidence=0.9,
            status="active"
        )
        
        db.add(test_pair)
        db.commit()
        db.refresh(test_pair)
        
        print(f"✅ Created test pair with ID: {test_pair.id}")
        print(f"   Equivalence Score: {test_pair.equivalence_score}")
        print(f"   Confidence: {test_pair.confidence}")
        print(f"   Status: {test_pair.status}")
        
        return test_pair
        
    except Exception as e:
        print(f"❌ Error creating test pair: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_kalshi_test_pair())
