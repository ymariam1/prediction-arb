#!/usr/bin/env python3
"""
Test script for Kalshi WebSocket connection.
Based on: https://docs.kalshi.com/api-reference/websockets/websocket-connection
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.kalshi_websocket_reader import KalshiWebSocketReader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_kalshi_websocket():
    """Test the Kalshi WebSocket implementation."""
    db = next(get_db())
    reader = KalshiWebSocketReader(db)
    
    # Add callbacks to see what data we receive
    async def on_orderbook_update(market_ticker, order_book):
        print(f"📊 Orderbook Update for {market_ticker}: {len(order_book['buys'])} buys, {len(order_book['sells'])} sells")
        if order_book['buys']:
            print(f"  Top buy: {order_book['buys'][0]}")
        if order_book['sells']:
            print(f"  Top sell: {order_book['sells'][0]}")
    
    async def on_ticker_update(market_ticker, last_price):
        print(f"💰 Ticker Update for {market_ticker}: {last_price}")
    
    async def on_trade_update(market_ticker, price, size):
        print(f"🔄 Trade for {market_ticker}: {size} @ {price}")
    
    reader.add_orderbook_callback(on_orderbook_update)
    reader.add_ticker_callback(on_ticker_update)
    reader.add_trade_callback(on_trade_update)
    
    try:
        print("🔌 Connecting to Kalshi WebSocket...")
        await reader.connect()
        
        # Subscribe to some test markets
        # Note: These are example market tickers - you'll need real ones
        test_markets = [
            "CPI-22DEC-TN0.1",  # Example from documentation
            "FED-22DEC-TN0.1"   # Another example
        ]
        
        print(f"📡 Subscribing to {len(test_markets)} markets...")
        await reader.subscribe_to_markets(test_markets)
        
        print("👂 Listening for real-time updates...")
        print("Press Ctrl+C to stop")
        
        # Listen for messages for 30 seconds
        await asyncio.wait_for(reader.listen(), timeout=30.0)
        
    except asyncio.TimeoutError:
        print("⏰ Test completed after 30 seconds")
    except KeyboardInterrupt:
        print("\n🛑 Stopping Kalshi WebSocket test...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await reader.disconnect()
        db.close()

if __name__ == "__main__":
    asyncio.run(test_kalshi_websocket())
