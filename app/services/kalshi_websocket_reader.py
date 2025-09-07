"""
Kalshi WebSocket-based data ingestion service for real-time market data.
Based on: https://docs.kalshi.com/api-reference/websockets/websocket-connection
"""
import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session

from app.services.base_reader import BaseVenueReader
from app.config import settings
from app.models.rules_text import RulesText
from app.models.book_levels import BookLevels


class KalshiWebSocketReader(BaseVenueReader):
    """Kalshi WebSocket-based venue data ingestion service."""
    
    def __init__(self, db: Session):
        super().__init__("kalshi", db)
        
        # Kalshi WebSocket configuration
        self.api_key = settings.kalshi_api_key_id
        self.wss_url = "wss://api.elections.kalshi.com"
        
        # WebSocket connection
        self.websocket = None
        self.connected = False
        self.subscribed_markets: set = set()
        
        # Callbacks for different event types
        self.orderbook_callbacks: List[Callable] = []
        self.ticker_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        
        # Connection management
        self.reconnect_interval = 10  # seconds
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0
        
    async def connect(self):
        """Connect to Kalshi WebSocket."""
        try:
            self.logger.info("Connecting to Kalshi WebSocket...")
            
            # Kalshi WebSocket connection with API key authentication
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            self.websocket = await websockets.connect(
                self.wss_url,
                extra_headers=headers
            )
            
            self.connected = True
            self.reconnect_attempts = 0
            self.logger.info("Connected to Kalshi WebSocket")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Kalshi WebSocket: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Kalshi WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            self.logger.info("Disconnected from Kalshi WebSocket")
    
    async def subscribe_to_markets(self, market_tickers: List[str]):
        """Subscribe to specific market tickers."""
        if not self.connected or not self.websocket:
            self.logger.error("WebSocket not connected")
            return
        
        try:
            # Kalshi subscription format
            subscription = {
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_ticker": market_tickers[0] if market_tickers else None
                }
            }
            
            await self.websocket.send(json.dumps(subscription))
            self.logger.info(f"Subscribed to markets: {market_tickers}")
            
            # Add to subscribed markets
            self.subscribed_markets.update(market_tickers)
            
        except Exception as e:
            self.logger.error(f"Error subscribing to markets: {e}")
    
    async def listen(self):
        """Listen for WebSocket messages and process them."""
        if not self.connected or not self.websocket:
            self.logger.error("WebSocket not connected")
            return
        
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Kalshi WebSocket connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error processing Kalshi WebSocket message: {e}")
    
    async def _process_message(self, message: str):
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribed":
                self.logger.info(f"Successfully subscribed: {data}")
            elif message_type == "ok":
                self.logger.info(f"Subscription confirmed: {data}")
            elif message_type == "orderbook_delta":
                await self._handle_orderbook_delta(data)
            elif message_type == "market_ticker":
                await self._handle_market_ticker(data)
            elif message_type == "trade":
                await self._handle_trade(data)
            elif message_type == "error":
                self.logger.error(f"Kalshi WebSocket error: {data}")
            else:
                self.logger.debug(f"Unknown Kalshi message type: {message_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Kalshi WebSocket message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing Kalshi WebSocket message: {e}")
    
    async def _handle_orderbook_delta(self, data: Dict[str, Any]):
        """Handle orderbook delta update from Kalshi WebSocket."""
        try:
            orderbook_data = data.get("data", {})
            market_ticker = orderbook_data.get("market_ticker")
            
            if not market_ticker:
                return
            
            # Process order book data
            order_book = {
                'buys': [],
                'sells': []
            }
            
            # Process bids (buy orders)
            for bid in orderbook_data.get("bids", []):
                order_book['buys'].append({
                    'price': float(bid.get('price', 0)),
                    'size': float(bid.get('size', 0))
                })
            
            # Process asks (sell orders)
            for ask in orderbook_data.get("asks", []):
                order_book['sells'].append({
                    'price': float(ask.get('price', 0)),
                    'size': float(ask.get('size', 0))
                })
            
            # Find the market ID for this ticker
            market_id = await self._find_market_for_ticker(market_ticker)
            if market_id:
                # Persist order book data
                await self._persist_order_book(market_id, order_book)
            
            # Notify callbacks
            for callback in self.orderbook_callbacks:
                try:
                    await callback(market_ticker, order_book)
                except Exception as e:
                    self.logger.error(f"Error in orderbook callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling orderbook delta: {e}")
    
    async def _handle_market_ticker(self, data: Dict[str, Any]):
        """Handle market ticker update from Kalshi WebSocket."""
        try:
            ticker_data = data.get("data", {})
            market_ticker = ticker_data.get("market_ticker")
            last_price = ticker_data.get("last_price")
            
            if market_ticker and last_price:
                self.logger.info(f"Market ticker update for {market_ticker}: {last_price}")
                
                # Notify callbacks
                for callback in self.ticker_callbacks:
                    try:
                        await callback(market_ticker, last_price)
                    except Exception as e:
                        self.logger.error(f"Error in ticker callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error handling market ticker: {e}")
    
    async def _handle_trade(self, data: Dict[str, Any]):
        """Handle trade update from Kalshi WebSocket."""
        try:
            trade_data = data.get("data", {})
            market_ticker = trade_data.get("market_ticker")
            price = trade_data.get("price")
            size = trade_data.get("size")
            
            if market_ticker and price and size:
                self.logger.info(f"Trade for {market_ticker}: {size} @ {price}")
                
                # Notify callbacks
                for callback in self.trade_callbacks:
                    try:
                        await callback(market_ticker, price, size)
                    except Exception as e:
                        self.logger.error(f"Error in trade callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error handling trade: {e}")
    
    async def _find_market_for_ticker(self, market_ticker: str) -> Optional[str]:
        """Find the market ID for a given market ticker."""
        try:
            # Query database for market with this ticker
            market = self.db.query(RulesText).filter(
                RulesText.venue_id == self.venue.id,
                RulesText.market_id == market_ticker
            ).first()
            
            return market.market_id if market else None
            
        except Exception as e:
            self.logger.error(f"Error finding market for ticker {market_ticker}: {e}")
            return None
    
    # Callback registration methods
    def add_orderbook_callback(self, callback: Callable):
        """Add a callback for orderbook updates."""
        self.orderbook_callbacks.append(callback)
    
    def add_ticker_callback(self, callback: Callable):
        """Add a callback for market ticker updates."""
        self.ticker_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable):
        """Add a callback for trade updates."""
        self.trade_callbacks.append(callback)
    
    # Required methods from BaseVenueReader
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets - not used in WebSocket mode."""
        return []
    
    async def fetch_order_book(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book - not used in WebSocket mode."""
        return {'buys': [], 'sells': []}
    
    async def fetch_trades(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch trades - not used in WebSocket mode."""
        return []
    
    async def run_continuous_ingestion(self, interval_seconds: int = 60):
        """Run continuous WebSocket-based ingestion."""
        self.logger.info(f"Starting Kalshi WebSocket continuous ingestion for {self.venue_name}")
        
        while True:
            try:
                if not self.connected:
                    await self.connect()
                
                # Listen for messages
                await self.listen()
                
            except Exception as e:
                self.logger.error(f"Error in Kalshi WebSocket continuous ingestion: {e}")
                self.connected = False
                
                # Attempt reconnection
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    self.logger.info(f"Attempting Kalshi reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
                    await asyncio.sleep(self.reconnect_interval)
                else:
                    self.logger.error("Max Kalshi reconnection attempts reached")
                    break
    
    async def run_market_discovery(self):
        """Run market discovery - not applicable for WebSocket mode."""
        self.logger.info("Kalshi WebSocket mode: Market discovery happens via real-time updates")
        return 0
