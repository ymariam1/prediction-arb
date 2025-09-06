#!/usr/bin/env python3
"""
Arbitrage Engine Runner

CLI script to run the arbitrage detection engine and manage arbitrage signals.
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.arbitrage_engine import arbitrage_engine
from app.database import get_db
from app.models.arbitrage_signals import ArbitrageSignals
from app.models.pairs import Pairs


async def analyze_arbitrage():
    """Run arbitrage analysis on all active pairs."""
    print("🔍 Starting arbitrage analysis...")
    
    try:
        signals = await arbitrage_engine.analyze_all_pairs()
        
        if signals:
            print(f"✅ Found {len(signals)} arbitrage signals")
            
            # Show top opportunities
            arbitrage_opportunities = [s for s in signals if s.is_arbitrage]
            if arbitrage_opportunities:
                print(f"💰 {len(arbitrage_opportunities)} profitable opportunities found!")
                
                for i, signal in enumerate(arbitrage_opportunities[:5], 1):
                    print(f"\n{i}. Signal {signal.id[:8]}...")
                    print(f"   Strategy: {signal.strategy}")
                    print(f"   Total Cost: {signal.total_cost:.4f}")
                    print(f"   Edge Buffer: {signal.edge_buffer:.4f}")
                    print(f"   Executable Size: ${signal.executable_size:.2f}")
                    print(f"   Confidence: {signal.confidence:.2f}")
                    print(f"   Markets: {signal.market_a_venue} ↔ {signal.market_b_venue}")
            else:
                print("❌ No profitable arbitrage opportunities found")
        else:
            print("❌ No arbitrage signals generated")
            
    except Exception as e:
        print(f"❌ Error during arbitrage analysis: {e}")
        return False
    
    return True


async def show_signals(limit=10, active_only=True):
    """Show recent arbitrage signals."""
    print(f"📊 Showing {limit} recent arbitrage signals...")
    
    try:
        signals = await arbitrage_engine.get_active_signals(limit=limit)
        
        if not signals:
            print("❌ No active signals found")
            return
        
        print(f"\n{'ID':<12} {'Strategy':<15} {'Cost':<8} {'Edge':<8} {'Size':<10} {'Conf':<6} {'Status':<10}")
        print("-" * 80)
        
        for signal in signals:
            print(f"{signal.id[:8]:<12} {signal.strategy:<15} {signal.total_cost:<8.4f} "
                  f"{signal.edge_buffer:<8.4f} ${signal.executable_size:<9.2f} "
                  f"{signal.confidence:<6.2f} {signal.status:<10}")
        
    except Exception as e:
        print(f"❌ Error getting signals: {e}")


async def show_stats():
    """Show arbitrage system statistics."""
    print("📈 Arbitrage System Statistics")
    print("=" * 40)
    
    db = next(get_db())
    
    try:
        # Count signals
        total_signals = db.query(ArbitrageSignals).count()
        active_signals = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.status == "active"
        ).count()
        arbitrage_opportunities = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.is_arbitrage == True,
            ArbitrageSignals.status == "active"
        ).count()
        
        # Count pairs
        total_pairs = db.query(Pairs).count()
        active_pairs = db.query(Pairs).filter(Pairs.status == "active").count()
        
        print(f"Signals:")
        print(f"  Total: {total_signals}")
        print(f"  Active: {active_signals}")
        print(f"  Arbitrage Opportunities: {arbitrage_opportunities}")
        print()
        print(f"Pairs:")
        print(f"  Total: {total_pairs}")
        print(f"  Active: {active_pairs}")
        
        # Show recent activity
        recent_signals = db.query(ArbitrageSignals).order_by(
            ArbitrageSignals.created_at.desc()
        ).limit(5).all()
        
        if recent_signals:
            print(f"\nRecent Signals:")
            for signal in recent_signals:
                status_icon = "💰" if signal.is_arbitrage else "📊"
                print(f"  {status_icon} {signal.id[:8]}... - {signal.strategy} - "
                      f"Cost: {signal.total_cost:.4f} - {signal.status}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        db.close()


async def cleanup_signals():
    """Clean up expired signals."""
    print("🧹 Cleaning up expired signals...")
    
    try:
        expired_count = await arbitrage_engine.cleanup_expired_signals()
        print(f"✅ Marked {expired_count} signals as expired")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")


async def test_arbitrage_engine():
    """Test the arbitrage engine with sample data."""
    print("🧪 Testing arbitrage engine...")
    
    try:
        # Get a sample pair to test
        db = next(get_db())
        sample_pair = db.query(Pairs).filter(
            Pairs.status == "active",
            Pairs.hard_ok == True
        ).first()
        
        if not sample_pair:
            print("❌ No active pairs found for testing")
            return
        
        print(f"Testing with pair: {sample_pair.id}")
        
        # Analyze the pair
        signal = await arbitrage_engine.analyze_pair(sample_pair)
        
        if signal:
            print(f"✅ Generated signal: {signal.id}")
            print(f"   Is Arbitrage: {signal.is_arbitrage}")
            print(f"   Total Cost: {signal.total_cost:.4f}")
            print(f"   Strategy: {signal.strategy}")
            print(f"   Confidence: {signal.confidence:.2f}")
        else:
            print("❌ No signal generated (likely missing order book data)")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Arbitrage Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    subparsers.add_parser("analyze", help="Run arbitrage analysis on all active pairs")
    
    # Show signals command
    signals_parser = subparsers.add_parser("signals", help="Show recent arbitrage signals")
    signals_parser.add_argument("--limit", type=int, default=10, help="Number of signals to show")
    signals_parser.add_argument("--all", action="store_true", help="Show all signals, not just active")
    
    # Stats command
    subparsers.add_parser("stats", help="Show arbitrage system statistics")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Clean up expired signals")
    
    # Test command
    subparsers.add_parser("test", help="Test the arbitrage engine")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run the appropriate command
    if args.command == "analyze":
        asyncio.run(analyze_arbitrage())
    elif args.command == "signals":
        asyncio.run(show_signals(limit=args.limit, active_only=not args.all))
    elif args.command == "stats":
        asyncio.run(show_stats())
    elif args.command == "cleanup":
        asyncio.run(cleanup_signals())
    elif args.command == "test":
        asyncio.run(test_arbitrage_engine())


if __name__ == "__main__":
    main()
