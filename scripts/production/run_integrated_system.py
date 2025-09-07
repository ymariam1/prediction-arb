#!/usr/bin/env python3
"""
Integrated system runner that demonstrates how the on-chain listener
integrates with the existing arbitrage detection system.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.ingestion_manager import DataIngestionManager
from app.services.arbitrage_engine import ArbitrageEngine
from app.services.poly_onchain_reader import PolyOnChainReader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_integrated_system():
    """Run the integrated system with on-chain listener and arbitrage detection."""
    db = next(get_db())
    
    # Initialize components
    ingestion_manager = DataIngestionManager(db)
    arbitrage_engine = ArbitrageEngine()
    
    # Get the on-chain reader
    onchain_reader = ingestion_manager.readers.get("polymarket_onchain")
    
    if not onchain_reader:
        print("❌ On-chain reader not found. Make sure Polymarket venue is configured.")
        return
    
    print("🚀 Starting Integrated Prediction Market Arbitrage System")
    print("=" * 60)
    print("Components:")
    print("  ✅ Data Ingestion Manager")
    print("  ✅ On-Chain Event Listener")
    print("  ✅ Arbitrage Detection Engine")
    print("=" * 60)
    
    # Add callbacks to demonstrate integration
    async def on_trade_executed(event_data):
        """Handle trade execution and trigger arbitrage analysis."""
        args = event_data.get('args', {})
        token_id = args.get('tokenId')
        amount = args.get('amount')
        
        print(f"🔄 TRADE DETECTED: Token {token_id}, Amount {amount}")
        
        # Trigger arbitrage analysis for affected markets
        try:
            signals = await arbitrage_engine.analyze_all_pairs()
            if signals:
                print(f"💰 ARBITRAGE OPPORTUNITIES: Found {len(signals)} signals")
                for signal in signals[:3]:  # Show top 3
                    print(f"  - Pair {signal.pair_id}: Edge {signal.edge_buffer:.2%}, Cost ${signal.total_cost:.2f}")
            else:
                print("  No arbitrage opportunities found")
        except Exception as e:
            print(f"  Error in arbitrage analysis: {e}")
    
    async def on_market_created(event_data):
        """Handle new market creation."""
        args = event_data.get('args', {})
        question_id = args.get('questionId')
        outcome_slot_count = args.get('outcomeSlotCount')
        
        print(f"🆕 NEW MARKET: Question {question_id.hex()}, Outcomes {outcome_slot_count}")
        
        # Trigger market discovery to find potential pairs
        try:
            results = await ingestion_manager.run_market_discovery(["polymarket"])
            print(f"  Market discovery completed: {results}")
        except Exception as e:
            print(f"  Error in market discovery: {e}")
    
    # Register callbacks
    onchain_reader.add_trade_executed_callback(on_trade_executed)
    onchain_reader.add_market_created_callback(on_market_created)
    
    try:
        print("\n📡 Starting on-chain event listener...")
        print("This will listen for:")
        print("  - Transfer events (trades)")
        print("  - ConditionPreparation events (new markets)")
        print("  - ConditionResolution events (market resolutions)")
        print("\nPress Ctrl+C to stop")
        print("-" * 60)
        
        # Start the on-chain listener
        await onchain_reader.run_continuous_ingestion()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping integrated system...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await onchain_reader.disconnect()
        db.close()
        print("✅ System stopped and cleaned up")

if __name__ == "__main__":
    asyncio.run(run_integrated_system())
