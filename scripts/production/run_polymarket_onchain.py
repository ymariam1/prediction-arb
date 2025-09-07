#!/usr/bin/env python3
"""
Run Polymarket on-chain event listener for real-time market data.
This script demonstrates how to use the on-chain listener to capture
real-time Polymarket events directly from the blockchain.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.poly_onchain_reader import PolyOnChainReader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main function to run the on-chain event listener."""
    db = next(get_db())
    reader = PolyOnChainReader(db)
    
    # Add callbacks to handle different types of events
    async def on_trade_executed(event_data):
        """Handle trade execution events."""
        args = event_data.get('args', {})
        token_id = args.get('tokenId')
        amount = args.get('amount')
        account = args.get('account')
        
        print(f"🔄 TRADE: Token {token_id}, Amount {amount}, Account {account}")
        
        # Here you could:
        # - Update order books
        # - Calculate arbitrage opportunities
        # - Send notifications
        # - Store trade data
    
    async def on_market_created(event_data):
        """Handle new market creation events."""
        args = event_data.get('args', {})
        question_id = args.get('questionId')
        outcome_slot_count = args.get('outcomeSlotCount')
        oracle = args.get('oracle')
        
        print(f"🆕 NEW MARKET: Question {question_id.hex()}, Outcomes {outcome_slot_count}, Oracle {oracle}")
        
        # Here you could:
        # - Add new market to database
        # - Start monitoring the new market
        # - Set up arbitrage detection
    
    async def on_market_resolved(event_data):
        """Handle market resolution events."""
        args = event_data.get('args', {})
        question_id = args.get('questionId')
        payout = args.get('payout')
        
        print(f"🏁 MARKET RESOLVED: Question {question_id.hex()}, Payout {payout}")
        
        # Here you could:
        # - Update market status
        # - Process payouts
        # - Clean up monitoring
    
    # Register callbacks
    reader.add_trade_executed_callback(on_trade_executed)
    reader.add_market_created_callback(on_market_created)
    
    try:
        print("🚀 Starting Polymarket On-Chain Event Listener")
        print("=" * 50)
        print("This will listen for:")
        print("  - Transfer events (trades)")
        print("  - ConditionPreparation events (new markets)")
        print("  - ConditionResolution events (market resolutions)")
        print("=" * 50)
        print("Press Ctrl+C to stop")
        print()
        
        # Start the continuous event listening
        await reader.run_continuous_ingestion()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping on-chain event listener...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await reader.disconnect()
        db.close()
        print("✅ Disconnected and cleaned up")

if __name__ == "__main__":
    asyncio.run(main())
