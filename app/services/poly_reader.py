"""
Polymarket venue data ingestion service.
"""
import asyncio
import aiohttp
import logging
import hmac
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.base_reader import BaseVenueReader
from app.config import settings
from app.models.rules_text import RulesText


class PolyReader(BaseVenueReader):
    """Polymarket venue data ingestion service."""
    
    def __init__(self, db: Session):
        super().__init__("polymarket", db)
        
        # Polymarket API configuration
        self.api_key = settings.polymarket_api_key
        self.api_secret = settings.polymarket_api_secret
        self.api_passphrase = settings.polymarket_api_passphrase
        # Use the main Polymarket API for markets, CLOB API for order books
        self.api_base_url = "https://clob.polymarket.com"
        self.clob_base_url = "https://clob.polymarket.com"
        
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            self.logger.warning("Polymarket API credentials not fully configured")
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Generate HMAC signature for Polymarket API authentication."""
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            return ""
        
        message = timestamp + method + request_path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _make_request(self, endpoint: str, method: str = "GET", use_clob: bool = False, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Polymarket API."""
        base_url = self.clob_base_url if use_clob else self.api_base_url
        url = f"{base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add authentication if credentials are available
        if all([self.api_key, self.api_secret, self.api_passphrase]):
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(timestamp, method, endpoint, kwargs.get('json', ''))
            
            headers.update({
                "POLY-ACCESS-KEY": self.api_key,
                "POLY-ACCESS-SIGNATURE": signature,
                "POLY-ACCESS-TIMESTAMP": timestamp,
                "POLY-ACCESS-PASSPHRASE": self.api_passphrase
            })
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            self.logger.error(f"Polymarket API error: {response.status} - {await response.text()}")
                            return {}
                else:
                    async with session.post(url, headers=headers, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            self.logger.error(f"Polymarket API error: {response.status} - {await response.text()}")
                            return {}
                            
            except Exception as e:
                self.logger.error(f"Error making request to Polymarket API: {e}")
                return {}
            
            finally:
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
    
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Polymarket."""
        try:
            # Get active markets using the main API
            response = await self._make_request("/markets?active=true")
            
            if not response or 'data' not in response:
                self.logger.warning("No markets data received from Polymarket")
                return []
            
            markets = []
            for market in response['data']:
                # Extract relevant market information
                # Determine market status based on active and closed flags
                is_active = market.get('active', False)
                is_closed = market.get('closed', False)
                
                if is_closed:
                    status = 'closed'
                elif is_active:
                    status = 'active'
                else:
                    status = 'inactive'
                
                market_data = {
                    'id': market.get('condition_id'),  # Use condition_id as the market ID
                    'title': market.get('question', ''),
                    'rules_text': market.get('description', ''),
                    'resolution_date': market.get('end_date_iso'),
                    'status': status,
                    'version': '1.0',
                    'category': None,  # Not available in current API
                    'subcategory': None,  # Not available in current API
                    'last_price': None,  # Not available in current API
                    'volume': None,  # Not available in current API
                    'open_interest': None,  # Not available in current API
                    'outcomes': market.get('tokens', [])
                }
                
                # Only include markets with valid IDs
                if market_data['id']:
                    markets.append(market_data)
            
            self.logger.info(f"Fetched {len(markets)} markets from Polymarket")
            return markets
            
        except Exception as e:
            self.logger.error(f"Error fetching markets from Polymarket: {e}")
            return []
    
    async def fetch_order_book(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book for a specific Polymarket market."""
        try:
            # First, get the market details to find token IDs
            market_details = await self.fetch_market_details(market_id)
            if not market_details or 'outcomes' not in market_details:
                self.logger.warning(f"No market details or outcomes found for market {market_id}")
                return {'buys': [], 'sells': []}
            
            # Combine order books from all outcomes (tokens) in the market
            combined_order_book = {
                'buys': [],
                'sells': []
            }
            
            for outcome in market_details['outcomes']:
                token_id = outcome.get('token_id')
                if not token_id:
                    continue
                
                # Fetch order book for this specific token
                token_order_book = await self._fetch_token_order_book(token_id)
                
                # Add outcome information to each order
                for buy_order in token_order_book.get('buys', []):
                    buy_order['outcome'] = outcome.get('outcome', '')
                    buy_order['token_id'] = token_id
                    combined_order_book['buys'].append(buy_order)
                
                for sell_order in token_order_book.get('sells', []):
                    sell_order['outcome'] = outcome.get('outcome', '')
                    sell_order['token_id'] = token_id
                    combined_order_book['sells'].append(sell_order)
            
            # Sort by price (bids descending, asks ascending)
            combined_order_book['buys'].sort(key=lambda x: x['price'], reverse=True)
            combined_order_book['sells'].sort(key=lambda x: x['price'])
            
            total_bids = len(combined_order_book['buys'])
            total_asks = len(combined_order_book['sells'])
            self.logger.debug(f"Fetched order book for market {market_id}: {total_bids} bids, {total_asks} asks across {len(market_details['outcomes'])} outcomes")
            
            return combined_order_book
            
        except Exception as e:
            self.logger.warning(f"Order book not available for market {market_id}: {e}")
            return {'buys': [], 'sells': []}
    
    async def _fetch_token_order_book(self, token_id: str) -> Dict[str, Any]:
        """Fetch order book for a specific token ID."""
        try:
            # Use the CLOB API for order books
            response = await self._make_request(f"/book?token_id={token_id}", use_clob=True)
            
            if not response:
                self.logger.debug(f"No order book data received for token {token_id}")
                return {'buys': [], 'sells': []}
            
            # Extract order book data according to Polymarket API format
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
            
            return order_book
            
        except Exception as e:
            self.logger.debug(f"Order book not available for token {token_id}: {e}")
            return {'buys': [], 'sells': []}
    
    async def fetch_trades(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch recent trades for a specific Polymarket market."""
        try:
            # Note: Trades endpoints may not be available for all markets
            # or may require different authentication/endpoints
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
                    'timestamp': trade.get('timestamp'),
                    'order_id': trade.get('order_id'),
                    'outcome': trade.get('outcome')
                }
                
                if trade_data['id']:
                    trades.append(trade_data)
            
            self.logger.debug(f"Fetched {len(trades)} trades for market {market_id}")
            return trades
            
        except Exception as e:
            self.logger.warning(f"Trades not available for market {market_id}: {e}")
            return []
    
    async def fetch_market_details(self, market_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific market."""
        try:
            # Use the main API for market details
            response = await self._make_request(f"/markets/{market_id}")
            
            if not response:
                self.logger.warning(f"No market details received for market {market_id}")
                return {}
            
            # Ensure the response has the expected structure
            if 'outcomes' not in response:
                # If outcomes are not in the response, try to construct them from tokens
                if 'tokens' in response:
                    response['outcomes'] = response['tokens']
                else:
                    self.logger.warning(f"No outcomes or tokens found in market details for {market_id}")
                    return {}
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error fetching market details for {market_id}: {e}")
            return {}
    
    async def fetch_market_outcomes(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch outcomes for a specific market."""
        try:
            response = await self._make_request(f"/markets/{market_id}/outcomes")
            
            if not response or 'outcomes' not in response:
                self.logger.warning(f"No outcomes data received for market {market_id}")
                return []
            
            return response['outcomes']
            
        except Exception as e:
            self.logger.error(f"Error fetching outcomes for market {market_id}: {e}")
            return []
    
    async def run_market_discovery(self):
        """Run a one-time market discovery to populate initial data."""
        self.logger.info("Starting Polymarket market discovery...")
        
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
