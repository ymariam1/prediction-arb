#!/usr/bin/env python3
"""
Create a profitable arbitrage opportunity for testing

This script creates a realistic arbitrage scenario that should trigger alerts.
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


async def create_profitable_arbitrage():
    """Create a profitable arbitrage opportunity."""
    print("💰 Creating profitable arbitrage opportunity...")
    
    db = next(get_db())
    
    try:
        # Create two markets with a clear arbitrage opportunity
        market1 = CanonicalMarket(
            rules_text_id="arb-test-1",
            canonical_id="kalshi_arbitrage-test-1_c1d2e3f4",
            question_text="Will Bitcoin reach $100,000 by end of 2024?",
            outcome_options=["Yes", "No"],
            resolution_criteria={
                "description": "Bitcoin must reach $100,000 USD by December 31, 2024",
                "deadline": "December 31, 2024",
                "authority": "Kalshi resolution"
            },
            category="crypto",
            tags=["bitcoin", "crypto", "price-target"]
        )
        
        market2 = CanonicalMarket(
            rules_text_id="arb-test-2",
            canonical_id="polymarket_arbitrage-test-2_d2e3f4g5", 
            question_text="Bitcoin hits $100K by end of 2024?",
            outcome_options=["Yes", "No"],
            resolution_criteria={
                "description": "Bitcoin must reach $100,000 USD by December 31, 2024",
                "deadline": "December 31, 2024", 
                "authority": "Polymarket resolution"
            },
            category="crypto",
            tags=["bitcoin", "crypto", "price-target"]
        )
        
        db.add(market1)
        db.add(market2)
        db.commit()
        db.refresh(market1)
        db.refresh(market2)
        
        print(f"✅ Created Market 1: {market1.canonical_id}")
        print(f"✅ Created Market 2: {market2.canonical_id}")
        
        # Create order book data with profitable arbitrage
        now_utc = datetime.now(timezone.utc)
        
        # Market 1 (Kalshi): Buy Yes at 0.45, Sell Yes at 0.46
        market1_data = [
            {"side": "bid", "level": 1, "price": 0.45, "size": 1000},
            {"side": "bid", "level": 2, "price": 0.44, "size": 2000},
            {"side": "ask", "level": 1, "price": 0.46, "size": 1200},
            {"side": "ask", "level": 2, "price": 0.47, "size": 1800},
        ]
        
        # Market 2 (Polymarket): Buy Yes at 0.48, Sell Yes at 0.49
        # This creates arbitrage: Buy at Kalshi (0.46) and Sell at Polymarket (0.48)
        market2_data = [
            {"side": "bid", "level": 1, "price": 0.48, "size": 800},
            {"side": "bid", "level": 2, "price": 0.47, "size": 1200},
            {"side": "ask", "level": 1, "price": 0.49, "size": 900},
            {"side": "ask", "level": 2, "price": 0.50, "size": 1100},
        ]
        
        # Create order book levels
        for data in market1_data:
            book_level = BookLevels(
                venue_id="03397cc4-806e-4503-aa20-5ddaef8a5a7c",  # Kalshi
                market_id=market1.canonical_id,
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=now_utc
            )
            db.add(book_level)
        
        for data in market2_data:
            book_level = BookLevels(
                venue_id="34cfc1d9-2d56-4c8f-9007-7379fd0e85e9",  # Polymarket
                market_id=market2.canonical_id,
                side=data["side"],
                level=data["level"],
                price=data["price"],
                size=data["size"],
                timestamp=now_utc
            )
            db.add(book_level)
        
        # Create pair
        pair = Pairs(
            market_a_id=market1.id,
            market_b_id=market2.id,
            equivalence_score=0.95,  # Very high - same question
            conflict_list=["Identical markets on different venues"],
            hard_ok=True,
            confidence=0.98,
            status="active"
        )
        
        db.add(pair)
        db.commit()
        db.refresh(pair)
        
        print(f"✅ Created profitable arbitrage pair")
        print(f"   Market 1 (Kalshi): Buy Yes at 0.45, Sell Yes at 0.46")
        print(f"   Market 2 (Polymarket): Buy Yes at 0.48, Sell Yes at 0.49")
        print(f"   💰 Expected arbitrage: Buy at 0.46, Sell at 0.48 = 4.3% profit")
        
        return market1, market2, pair
        
    except Exception as e:
        print(f"❌ Error creating profitable arbitrage: {e}")
        db.rollback()
        return None, None, None
    finally:
        db.close()


async def test_profitable_arbitrage():
    """Test the profitable arbitrage detection."""
    print("🔍 Testing profitable arbitrage detection...")
    
    try:
        # Run arbitrage analysis
        signals = await arbitrage_engine.analyze_all_pairs()
        
        print(f"📊 Found {len(signals)} arbitrage signals")
        
        profitable_signals = [s for s in signals if s.is_arbitrage]
        
        if profitable_signals:
            print(f"🎉 SUCCESS! Found {len(profitable_signals)} profitable arbitrage opportunities!")
            
            for signal in profitable_signals:
                profit_pct = (1.0 - signal.total_cost) * 100
                profit_amount = signal.executable_size * (1.0 - signal.total_cost)
                
                print(f"\n💰 PROFITABLE ARBITRAGE DETECTED!")
                print(f"   Strategy: {signal.strategy}")
                print(f"   Profit: {profit_pct:.2f}% (${profit_amount:.2f})")
                print(f"   Executable Size: ${signal.executable_size:.2f}")
                print(f"   Confidence: {signal.confidence:.2f}")
                print(f"   Market A: {signal.market_a_venue} - Bid: {signal.market_a_best_bid:.4f}, Ask: {signal.market_a_best_ask:.4f}")
                print(f"   Market B: {signal.market_b_venue} - Bid: {signal.market_b_best_bid:.4f}, Ask: {signal.market_b_best_ask:.4f}")
        else:
            print("📊 No profitable arbitrage opportunities found")
            
            # Show the signals that were found
            for signal in signals:
                loss_pct = (signal.total_cost - 1.0) * 100
                print(f"   Signal: {signal.strategy} - Loss: {loss_pct:.2f}% (Cost: {signal.total_cost:.4f})")
        
        return signals
        
    except Exception as e:
        print(f"❌ Error in arbitrage detection: {e}")
        return []


async def main():
    """Main test function."""
    print("💰 Profitable Arbitrage Test")
    print("=" * 50)
    print("Creating a clear arbitrage opportunity:")
    print("Market 1 (Kalshi): Buy Yes at 0.45, Sell Yes at 0.46")
    print("Market 2 (Polymarket): Buy Yes at 0.48, Sell Yes at 0.49")
    print("Expected: Buy at 0.46, Sell at 0.48 = 4.3% profit")
    print("=" * 50)
    
    # Create profitable arbitrage
    market1, market2, pair = await create_profitable_arbitrage()
    if not all([market1, market2, pair]):
        print("❌ Failed to create profitable arbitrage")
        return
    
    # Test detection
    signals = await test_profitable_arbitrage()
    
    if signals:
        profitable = [s for s in signals if s.is_arbitrage]
        if profitable:
            print(f"\n🎉 TEST PASSED! System successfully detected profitable arbitrage!")
            print("✅ The monitoring system will catch opportunities like this in real-time!")
        else:
            print(f"\n⚠️  Test completed but no profitable opportunities detected")
            print("This might indicate an issue with the arbitrage calculation logic")
    else:
        print("❌ No signals generated - there may be an issue with the system")


if __name__ == "__main__":
    asyncio.run(main())
