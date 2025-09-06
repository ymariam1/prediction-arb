#!/usr/bin/env python3
"""
Test script for the arbitrage detection engine.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.arbitrage_engine import arbitrage_engine
from app.database import get_db
from app.models.pairs import Pairs
from app.models.canonical_market import CanonicalMarket
from app.models.book_levels import BookLevels


async def test_arbitrage_engine():
    """Test the arbitrage engine functionality."""
    print("🧪 Testing Arbitrage Engine")
    print("=" * 50)
    
    # Test 1: Check if we have any pairs
    print("\n1. Checking for available pairs...")
    db = next(get_db())
    
    try:
        pairs_count = db.query(Pairs).count()
        active_pairs_count = db.query(Pairs).filter(Pairs.status == "active").count()
        
        print(f"   Total pairs: {pairs_count}")
        print(f"   Active pairs: {active_pairs_count}")
        
        if active_pairs_count == 0:
            print("   ❌ No active pairs found. Run normalization pipeline first.")
            return
        
        # Test 2: Check for order book data
        print("\n2. Checking for order book data...")
        book_count = db.query(BookLevels).count()
        print(f"   Total order book records: {book_count}")
        
        if book_count == 0:
            print("   ❌ No order book data found. Run ingestion first.")
            return
        
        # Test 3: Test single pair analysis
        print("\n3. Testing single pair analysis...")
        sample_pair = db.query(Pairs).filter(
            Pairs.status == "active",
            Pairs.hard_ok == True
        ).first()
        
        if not sample_pair:
            print("   ❌ No suitable pair found for testing")
            return
        
        print(f"   Testing pair: {sample_pair.id}")
        print(f"   Equivalence score: {sample_pair.equivalence_score}")
        
        signal = await arbitrage_engine.analyze_pair(sample_pair)
        
        if signal:
            print(f"   ✅ Signal generated: {signal.id}")
            print(f"   Is arbitrage: {signal.is_arbitrage}")
            print(f"   Total cost: {signal.total_cost:.4f}")
            print(f"   Edge buffer: {signal.edge_buffer:.4f}")
            print(f"   Strategy: {signal.strategy}")
            print(f"   Confidence: {signal.confidence:.2f}")
            print(f"   Executable size: ${signal.executable_size:.2f}")
        else:
            print("   ❌ No signal generated (likely missing order book data)")
        
        # Test 4: Test full analysis
        print("\n4. Testing full arbitrage analysis...")
        signals = await arbitrage_engine.analyze_all_pairs()
        
        print(f"   Generated {len(signals)} signals")
        
        arbitrage_opportunities = [s for s in signals if s.is_arbitrage]
        print(f"   Found {len(arbitrage_opportunities)} arbitrage opportunities")
        
        if arbitrage_opportunities:
            print("\n   Top opportunities:")
            for i, signal in enumerate(arbitrage_opportunities[:3], 1):
                print(f"   {i}. {signal.strategy} - Cost: {signal.total_cost:.4f} - "
                      f"Edge: {signal.edge_buffer:.4f} - Size: ${signal.executable_size:.2f}")
        
        # Test 5: Test signal retrieval
        print("\n5. Testing signal retrieval...")
        active_signals = await arbitrage_engine.get_active_signals(limit=5)
        print(f"   Retrieved {len(active_signals)} active signals")
        
        # Test 6: Test cleanup
        print("\n6. Testing signal cleanup...")
        expired_count = await arbitrage_engine.cleanup_expired_signals()
        print(f"   Cleaned up {expired_count} expired signals")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def create_test_data():
    """Create test data for arbitrage engine testing."""
    print("🔧 Creating test data for arbitrage engine...")
    
    db = next(get_db())
    
    try:
        # Check if we have any canonical markets
        markets_count = db.query(CanonicalMarket).count()
        print(f"Canonical markets: {markets_count}")
        
        if markets_count == 0:
            print("❌ No canonical markets found. Run normalization pipeline first.")
            return
        
        # Check if we have any order book data
        books_count = db.query(BookLevels).count()
        print(f"Order book records: {books_count}")
        
        if books_count == 0:
            print("❌ No order book data found. Run ingestion first.")
            return
        
        print("✅ Test data is available")
        
    except Exception as e:
        print(f"❌ Error checking test data: {e}")
    finally:
        db.close()


def main():
    """Main test function."""
    print("Arbitrage Engine Test Suite")
    print("=" * 50)
    
    # Check test data first
    asyncio.run(create_test_data())
    
    # Run main tests
    asyncio.run(test_arbitrage_engine())


if __name__ == "__main__":
    main()
