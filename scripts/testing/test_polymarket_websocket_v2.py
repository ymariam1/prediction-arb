#!/usr/bin/env python3
"""
Test script for the new Polymarket WebSocket implementation.
Based on: https://github.com/nevuamarkets/poly-websockets
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.poly_websocket_v2 import PolyWebSocketV2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_websocket_v2():
    """Test the new WebSocket implementation."""
    db = next(get_db())
    reader = PolyWebSocketV2(db)
    
    # Add callbacks to see what data we receive
    async def on_book_update(asset_id, order_book):
        print(f"📊 Book Update for {asset_id[:20]}...: {len(order_book['buys'])} buys, {len(order_book['sells'])} sells")
        if order_book['buys']:
            print(f"  Top buy: {order_book['buys'][0]}")
        if order_book['sells']:
            print(f"  Top sell: {order_book['sells'][0]}")
    
    async def on_price_change(asset_id, new_price):
        print(f"💰 Price Change for {asset_id[:20]}...: {new_price}")
    
    async def on_tick_size_change(asset_id, new_tick_size):
        print(f"📏 Tick Size Change for {asset_id[:20]}...: {new_tick_size}")
    
    async def on_last_trade_price(asset_id, last_price):
        print(f"🔄 Last Trade Price for {asset_id[:20]}...: {last_price}")
    
    reader.add_book_callback(on_book_update)
    reader.add_price_change_callback(on_price_change)
    reader.add_tick_size_change_callback(on_tick_size_change)
    reader.add_last_trade_price_callback(on_last_trade_price)
    
    try:
        print("🔌 Connecting to Polymarket WebSocket V2...")
        await reader.connect()
        
        # Add some real asset subscriptions from current markets
        test_assets = [
            "14270523446080509320829200481895961480205553513304203367521919818541658424782",  # Chiefs
            "93110170397161149119544349457822484949376809039410140245101963942162463626903",  # Raiders
            "11285628865066765501285628865066765501285628865066765501285628865066765501285",  # Yes
            "10019132116189403893100191321161894038931001913211618940389310019132116189403893"   # No
        ]
        
        print(f"📡 Adding subscriptions for {len(test_assets)} assets...")
        await reader.add_subscriptions(test_assets)
        
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
    asyncio.run(test_websocket_v2())
