#!/usr/bin/env python3
"""
Script to manually create a test pair for arbitrage testing
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.pairs import Pairs
from app.models.canonical_market import CanonicalMarket


async def create_test_pair():
    """Create a test pair for arbitrage testing."""
    print("🔗 Creating a test pair for arbitrage testing...")
    
    db = next(get_db())
    
    try:
        # Get two markets from different venues
        kalshi_markets = db.query(CanonicalMarket).join(
            CanonicalMarket.rules_text
        ).filter(
            CanonicalMarket.rules_text.has(venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c")
        ).limit(1).all()
        
        polymarket_markets = db.query(CanonicalMarket).join(
            CanonicalMarket.rules_text
        ).filter(
            CanonicalMarket.rules_text.has(venue_id="34cfc1d9-2d56-4c8f-9007-7379fd0e85e9")
        ).limit(1).all()
        
        if not kalshi_markets or not polymarket_markets:
            print("❌ Need at least one market from each venue")
            return
        
        market_a = kalshi_markets[0]
        market_b = polymarket_markets[0]
        
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
    asyncio.run(create_test_pair())
