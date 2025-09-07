#!/usr/bin/env python3
"""
Test script for Polymarket WebSocket connection.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.poly_websocket_reader import PolyWebSocketReader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_websocket_connection():
    """Test WebSocket connection to Polymarket."""
    db = next(get_db())
    reader = PolyWebSocketReader(db)
    
    # Add callbacks to see what data we receive
    async def on_market_update(market):
        print(f"📊 Market Update: {market['title'][:50]}... (Status: {market['status']})")
    
    async def on_orderbook_update(asset_id, order_book):
        print(f"📈 Order Book Update for {asset_id[:20]}...: {len(order_book['buys'])} buys, {len(order_book['sells'])} sells")
    
    async def on_trade_update(trade):
        print(f"💰 Trade Update: {trade['side']} {trade['size']} @ {trade['price']}")
    
    reader.add_market_callback(on_market_update)
    reader.add_orderbook_callback(on_orderbook_update)
    reader.add_trade_callback(on_trade_update)
    
    try:
        print("🔌 Connecting to Polymarket WebSocket...")
        await reader.connect()
        
        print("👂 Listening for real-time updates...")
        print("Press Ctrl+C to stop")
        
        # Listen for messages for 30 seconds
        await asyncio.wait_for(reader.listen(), timeout=30.0)
        
    except asyncio.TimeoutError:
        print("⏰ Test completed after 30 seconds")
    except KeyboardInterrupt:
        print("\n🛑 Stopping WebSocket test...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await reader.disconnect()
        db.close()

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
