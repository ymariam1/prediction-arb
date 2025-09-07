#!/usr/bin/env python3
"""
Test script for MrBeast arbitrage opportunity

This script creates mock markets based on the real Polymarket data to test
if our arbitrage detection system can identify the opportunity.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.canonical_market import CanonicalMarket
from app.models.book_levels import BookLevels
from app.models.pairs import Pairs
from app.services.arbitrage_engine import arbitrage_engine


async def create_mrbeast_test_markets():
    """Create mock markets based on the real Polymarket MrBeast data."""
    print("🎯 Creating MrBeast test markets...")
    
    db = next(get_db())
    
    try:
        # Create two test markets based on the real Polymarket data
        market1 = CanonicalMarket(
            rules_text_id="test-rules-1",
            canonical_id="polymarket_mrbeast-40m-binary_a1b2c3d4",
            question_text="Will MrBeast raise $40M for clean water by August 31?",
            outcome_options=["Yes", "No"],
            resolution_criteria={
                "description": "MrBeast must raise $40M for clean water by August 31, 2025",
                "deadline": "August 31, 2025",
                "authority": "Polymarket resolution"
            },
            category="charity",
            tags=["mrbeast", "fundraising", "clean-water", "charity"]
        )
        
        market2 = CanonicalMarket(
            rules_text_id="test-rules-2", 
            canonical_id="polymarket_mrbeast-40m-date_b2c3d4e5",
            question_text="MrBeast raises $40M on...?",
            outcome_options=["Sunday, August 31", "Saturday, August 30", "Monday, September 1", "September 2 or later"],
            resolution_criteria={
                "description": "The specific date when MrBeast raises $40M",
                "deadline": "When fundraising is complete",
                "authority": "Polymarket resolution"
            },
            category="charity",
            tags=["mrbeast", "fundraising", "date", "charity"]
        )
        
        db.add(market1)
        db.add(market2)
        db.commit()
        db.refresh(market1)
        db.refresh(market2)
        
        print(f"✅ Created Market 1: {market1.canonical_id}")
        print(f"✅ Created Market 2: {market2.canonical_id}")
        
        return market1, market2
        
    except Exception as e:
        print(f"❌ Error creating markets: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()


async def create_mrbeast_order_books(market1, market2):
    """Create order book data based on the real Polymarket prices."""
    print("📊 Creating order book data...")
    
    db = next(get_db())
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Market 1: Binary market - "Will MrBeast raise $40M by August 31?"
        # Real data: Yes 90¢, No 12¢ (89% chance)
        market1_data = [
            # Bids (buy orders)
            {"side": "bid", "level": 1, "price": 0.89, "size": 1000},  # Buy Yes at 89¢
            {"side": "bid", "level": 2, "price": 0.88, "size": 2000},
            {"side": "bid", "level": 3, "price": 0.87, "size": 1500},
            
            # Asks (sell orders) 
            {"side": "ask", "level": 1, "price": 0.90, "size": 1200},  # Sell Yes at 90¢
            {"side": "ask", "level": 2, "price": 0.91, "size": 1800},
            {"side": "ask", "level": 3, "price": 0.92, "size": 900},
        ]
        
        # Market 2: Date market - "MrBeast raises $40M on...?"
        # Real data: Sunday August 31 at 80% (Yes 81¢, No 22¢)
        market2_data = [
            # Bids (buy orders)
            {"side": "bid", "level": 1, "price": 0.79, "size": 800},   # Buy Sunday Aug 31 at 79¢
            {"side": "bid", "level": 2, "price": 0.78, "size": 1200},
            {"side": "bid", "level": 3, "price": 0.77, "size": 1000},
            
            # Asks (sell orders)
            {"side": "ask", "level": 1, "price": 0.81, "size": 900},   # Sell Sunday Aug 31 at 81¢
            {"side": "ask", "level": 2, "price": 0.82, "size": 1100},
            {"side": "ask", "level": 3, "price": 0.83, "size": 700},
        ]
        
        # Create order book levels for market 1
        for data in market1_data:
            book_level = BookLevels(
                venue_id="34cfc1d9-2d56-4c8f-9007-7379fd0e85e9",  # Polymarket venue ID
                market_id=market1.canonical_id,
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=now_utc
            )
            db.add(book_level)
        
        # Create order book levels for market 2
        for data in market2_data:
            book_level = BookLevels(
                venue_id="34cfc1d9-2d56-4c8f-9007-7379fd0e85e9",  # Polymarket venue ID
                market_id=market2.canonical_id,
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=now_utc
            )
            db.add(book_level)
        
        db.commit()
        print(f"✅ Created {len(market1_data)} order book levels for Market 1")
        print(f"✅ Created {len(market2_data)} order book levels for Market 2")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating order books: {e}")
        db.rollback()
        return False
    finally:
        db.close()


async def create_mrbeast_pair(market1, market2):
    """Create a pair between the two MrBeast markets."""
    print("🔗 Creating market pair...")
    
    db = next(get_db())
    
    try:
        # Create a pair with high equivalence score since they're related
        pair = Pairs(
            market_a_id=market1.id,
            market_b_id=market2.id,
            equivalence_score=0.85,  # High score - they're both about MrBeast raising $40M
            conflict_list=["Both markets are about MrBeast raising $40M, but one is binary and one is date-specific"],
            hard_ok=True,
            confidence=0.90,
            status="active"
        )
        
        db.add(pair)
        db.commit()
        db.refresh(pair)
        
        print(f"✅ Created pair: {market1.canonical_id} ↔ {market2.canonical_id}")
        print(f"   Equivalence Score: {pair.equivalence_score}")
        print(f"   Confidence: {pair.confidence}")
        
        return pair
        
    except Exception as e:
        print(f"❌ Error creating pair: {e}")
        db.rollback()
        return None
    finally:
        db.close()


async def test_arbitrage_detection():
    """Test if the arbitrage detection system can find the opportunity."""
    print("🔍 Testing arbitrage detection...")
    
    try:
        # Run arbitrage analysis
        signals = await arbitrage_engine.analyze_all_pairs()
        
        print(f"📊 Found {len(signals)} arbitrage signals")
        
        for signal in signals:
            print(f"\n🚨 Signal Details:")
            print(f"   ID: {signal.id[:8]}...")
            print(f"   Strategy: {signal.strategy}")
            print(f"   Total Cost: {signal.total_cost:.4f}")
            print(f"   Is Arbitrage: {signal.is_arbitrage}")
            print(f"   Edge Buffer: {signal.edge_buffer:.4f}")
            print(f"   Executable Size: ${signal.executable_size:.2f}")
            print(f"   Confidence: {signal.confidence:.2f}")
            
            if signal.is_arbitrage:
                profit_pct = (1.0 - signal.total_cost) * 100
                profit_amount = signal.executable_size * (1.0 - signal.total_cost)
                print(f"   💰 PROFIT: {profit_pct:.2f}% (${profit_amount:.2f})")
            else:
                loss_pct = (signal.total_cost - 1.0) * 100
                print(f"   ❌ Loss: {loss_pct:.2f}%")
        
        return signals
        
    except Exception as e:
        print(f"❌ Error in arbitrage detection: {e}")
        return []


async def main():
    """Main test function."""
    print("🎯 MrBeast Arbitrage Test")
    print("=" * 50)
    print("Testing with real Polymarket data:")
    print("Market 1: Will MrBeast raise $40M by August 31? (Yes 90¢, No 12¢)")
    print("Market 2: MrBeast raises $40M on...? (Sunday Aug 31: 81¢)")
    print("=" * 50)
    
    # Create test markets
    market1, market2 = await create_mrbeast_test_markets()
    if not market1 or not market2:
        print("❌ Failed to create test markets")
        return
    
    # Create order book data
    success = await create_mrbeast_order_books(market1, market2)
    if not success:
        print("❌ Failed to create order book data")
        return
    
    # Create market pair
    pair = await create_mrbeast_pair(market1, market2)
    if not pair:
        print("❌ Failed to create market pair")
        return
    
    # Test arbitrage detection
    signals = await test_arbitrage_detection()
    
    if signals:
        print(f"\n✅ Test completed! Found {len(signals)} signals")
        
        # Check if any are profitable
        profitable = [s for s in signals if s.is_arbitrage]
        if profitable:
            print(f"🎉 SUCCESS! Found {len(profitable)} profitable arbitrage opportunities!")
        else:
            print("📊 No profitable opportunities found (this is normal for this test case)")
    else:
        print("❌ No signals generated")


if __name__ == "__main__":
    asyncio.run(main())
