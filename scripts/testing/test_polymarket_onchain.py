#!/usr/bin/env python3
"""
Test script for Polymarket on-chain event listener.
Based on: https://polygonscan.com/address/0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
"""
import asyncio
import sys
import logging
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

async def test_polymarket_onchain():
    """Test the Polymarket on-chain event listener."""
    db = next(get_db())
    reader = PolyOnChainReader(db)
    
    # Add callbacks to see what events we receive
    async def on_trade_executed(event_data):
        print(f"🔄 Trade Executed: {event_data}")
    
    async def on_market_created(event_data):
        print(f"🆕 Market Created: {event_data}")
    
    reader.add_trade_executed_callback(on_trade_executed)
    reader.add_market_created_callback(on_market_created)
    
    try:
        print("🔌 Connecting to Polygon blockchain...")
        await reader.connect()
        
        print("👂 Listening for on-chain events...")
        print("This will listen for:")
        print("  - Transfer events (trades)")
        print("  - ConditionPreparation events (new markets)")
        print("  - ConditionResolution events (market resolutions)")
        print("Press Ctrl+C to stop")
        
        # Listen for events for 60 seconds
        await asyncio.wait_for(reader.listen_for_events(), timeout=60.0)
        
    except asyncio.TimeoutError:
        print("⏰ Test completed after 60 seconds")
    except KeyboardInterrupt:
        print("\n🛑 Stopping on-chain event listener...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await reader.disconnect()
        db.close()

if __name__ == "__main__":
    asyncio.run(test_polymarket_onchain())
