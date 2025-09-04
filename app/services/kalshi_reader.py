"""
Kalshi venue data ingestion service.
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.base_reader import BaseVenueReader
from app.config import settings
from app.models.rules_text import RulesText


class KalshiReader(BaseVenueReader):
    """Kalshi venue data ingestion service."""
    
    def __init__(self, db: Session):
        super().__init__("kalshi", db)
        
        # Kalshi API configuration
        self.api_key_id = settings.kalshi_api_key_id
        self.api_private_key = settings.kalshi_api_private_key
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"  # Updated API endpoint
        
        if not self.api_key_id or not self.api_private_key:
            self.logger.warning("Kalshi API credentials not configured")
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        
    async def _make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Kalshi API."""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add authentication if credentials are available
        if self.api_key_id and self.api_private_key:
            headers["Authorization"] = f"Bearer {self.api_key_id}"
            # Note: Kalshi may require additional authentication headers
            # Check their documentation for the exact format
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            self.logger.error(f"Kalshi API error: {response.status} - {await response.text()}")
                            return {}
                else:
                    async with session.post(url, headers=headers, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            self.logger.error(f"Kalshi API error: {response.status} - {await response.text()}")
                            return {}
                            
            except Exception as e:
                self.logger.error(f"Error making request to Kalshi API: {e}")
                return {}
            
            finally:
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
    
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Kalshi."""
        try:
            # Get all markets
            response = await self._make_request("/markets")
            
            if not response or 'markets' not in response:
                self.logger.warning("No markets data received from Kalshi")
                return []
            
            markets = []
            for market in response['markets']:
                # Extract relevant market information
                market_data = {
                    'id': market.get('ticker'),
                    'title': market.get('title'),
                    'rules_text': market.get('description', ''),
                    'resolution_date': market.get('expected_expiration_time'),
                    'status': market.get('status', 'active'),
                    'version': '1.0',
                    'category': market.get('category'),
                    'subcategory': market.get('subcategory'),
                    'last_price': market.get('last_price'),
                    'volume': market.get('volume'),
                    'open_interest': market.get('open_interest')
                }
                
                # Only include markets with valid IDs
                if market_data['id']:
                    markets.append(market_data)
            
            self.logger.info(f"Fetched {len(markets)} markets from Kalshi")
            return markets
            
        except Exception as e:
            self.logger.error(f"Error fetching markets from Kalshi: {e}")
            return []
    
    async def fetch_order_book(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book for a specific Kalshi market."""
        try:
            response = await self._make_request(f"/markets/{market_id}/orderbook")
            
            if not response:
                self.logger.warning(f"No order book data received for market {market_id}")
                return {'buys': [], 'sells': []}
            
            # Extract order book data
            order_book = {
                'buys': [],
                'sells': []
            }
            
            # Process buy orders (bids)
            if 'bids' in response:
                for bid in response['bids']:
                    order_book['buys'].append({
                        'price': float(bid.get('price', 0)),
                        'size': float(bid.get('size', 0))
                    })
            
            # Process sell orders (asks)
            if 'asks' in response:
                for ask in response['asks']:
                    order_book['sells'].append({
                        'price': float(ask.get('price', 0)),
                        'size': float(ask.get('size', 0))
                    })
            
            # Sort by price (bids descending, asks ascending)
            order_book['buys'].sort(key=lambda x: x['price'], reverse=True)
            order_book['sells'].sort(key=lambda x: x['price'])
            
            self.logger.debug(f"Fetched order book for market {market_id}: {len(order_book['buys'])} bids, {len(order_book['sells'])} asks")
            return order_book
            
        except Exception as e:
            self.logger.error(f"Error fetching order book for market {market_id}: {e}")
            return {'buys': [], 'sells': []}
    
    async def fetch_trades(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch recent trades for a specific Kalshi market."""
        try:
            response = await self._make_request(f"/markets/{market_id}/trades")
            
            if not response or 'trades' not in response:
                self.logger.warning(f"No trades data received for market {market_id}")
                return []
            
            trades = []
            for trade in response['trades']:
                trade_data = {
                    'id': trade.get('id'),
                    'price': float(trade.get('price', 0)),
                    'size': float(trade.get('size', 0)),
                    'side': trade.get('side', 'unknown'),
                    'timestamp': trade.get('created_time'),
                    'order_id': trade.get('order_id')
                }
                
                if trade_data['id']:
                    trades.append(trade_data)
            
            self.logger.debug(f"Fetched {len(trades)} trades for market {market_id}")
            return trades
            
        except Exception as e:
            self.logger.error(f"Error fetching trades for market {market_id}: {e}")
            return []
    
    async def fetch_market_details(self, market_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific market."""
        try:
            response = await self._make_request(f"/markets/{market_id}")
            
            if not response:
                self.logger.warning(f"No market details received for market {market_id}")
                return {}
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error fetching market details for {market_id}: {e}")
            return {}
    
    async def run_market_discovery(self):
        """Run a one-time market discovery to populate initial data."""
        self.logger.info("Starting Kalshi market discovery...")
        
        try:
            # Fetch and ingest all markets
            markets_count = await self.ingest_markets()
            
            if markets_count > 0:
                # Get market IDs for order book and trade ingestion
                active_markets = self.db.query(RulesText).filter(
                    RulesText.venue_id == self.venue.id,
                    RulesText.market_status == "active"
                ).all()
                
                market_ids = [m.market_id for m in active_markets]
                
                # Ingest order books and trades for discovered markets
                await self.ingest_order_books(market_ids)
                await self.ingest_trades(market_ids)
                
                self.logger.info(f"Market discovery completed. Found {markets_count} active markets.")
            else:
                self.logger.warning("No markets discovered during market discovery.")
                
        except Exception as e:
            self.logger.error(f"Error during market discovery: {e}")
            raise
