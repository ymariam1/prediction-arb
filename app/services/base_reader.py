"""
Base class for venue data ingestion services.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio
import logging
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venue import Venue
from app.models.rules_text import RulesText
from app.models.book_levels import BookLevels


class BaseVenueReader(ABC):
    """Abstract base class for venue data ingestion services."""
    
    def __init__(self, venue_name: str, db: Session):
        self.venue_name = venue_name
        self.db = db
        self.venue = self._get_venue()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        

        self.max_resolution_days = 28
        
    def _get_venue(self) -> Venue:
        """Get or create the venue record."""
        venue = self.db.query(Venue).filter(Venue.name == self.venue_name).first()
        if not venue:
            raise ValueError(f"Venue '{self.venue_name}' not found in database")
        return venue
    
    def _is_within_resolution_window(self, resolution_date: datetime) -> bool:
        """Check if market resolves within the 7-day window."""
        if not resolution_date:
            return False
        
        # Handle timezone-aware vs naive datetimes
        if resolution_date.tzinfo is None:
            # If resolution_date is naive, use UTC
            now = datetime.utcnow()
        else:
            # If resolution_date is timezone-aware, use timezone-aware now
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        cutoff_date = now + timedelta(days=self.max_resolution_days)
        return resolution_date <= cutoff_date
    
    @abstractmethod
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from the venue."""
        pass
    
    @abstractmethod
    async def fetch_order_book(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book for a specific market."""
        pass
    
    @abstractmethod
    async def fetch_trades(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch recent trades for a specific market."""
        pass
    
    async def ingest_markets(self) -> int:
        """Ingest markets data, filtering for 7-day resolution window."""
        try:
            markets = await self.fetch_markets()
            ingested_count = 0
            
            for market in markets:
                if self._should_ingest_market(market):
                    await self._persist_market(market)
                    ingested_count += 1
            
            self.logger.info(f"Ingested {ingested_count} markets from {self.venue_name}")
            return ingested_count
            
        except Exception as e:
            self.logger.error(f"Error ingesting markets from {self.venue_name}: {e}")
            raise
    
    async def ingest_order_books(self, market_ids: Optional[List[str]] = None) -> int:
        """Ingest order book data for specified markets or all active markets."""
        try:
            if market_ids is None:
                # Get all active markets for this venue
                active_markets = self.db.query(RulesText).filter(
                    RulesText.venue_id == self.venue.id,
                    RulesText.market_status == "active"
                ).all()
                market_ids = [m.market_id for m in active_markets]
            
            ingested_count = 0
            for market_id in market_ids:
                try:
                    order_book = await self.fetch_order_book(market_id)
                    await self._persist_order_book(market_id, order_book)
                    ingested_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to ingest order book for market {market_id}: {e}")
                    continue
            
            self.logger.info(f"Ingested order books for {ingested_count} markets from {self.venue_name}")
            return ingested_count
            
        except Exception as e:
            self.logger.error(f"Error ingesting order books from {self.venue_name}: {e}")
            raise
    
    async def ingest_trades(self, market_ids: Optional[List[str]] = None) -> int:
        """Ingest trade data for specified markets or all active markets."""
        try:
            if market_ids is None:
                # Get all active markets for this venue
                active_markets = self.db.query(RulesText).filter(
                    RulesText.venue_id == self.venue.id,
                    RulesText.market_status == "active"
                ).all()
                market_ids = [m.market_id for m in active_markets]
            
            ingested_count = 0
            for market_id in market_ids:
                try:
                    trades = await self.fetch_trades(market_id)
                    await self._persist_trades(market_id, trades)
                    ingested_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to ingest trades for market {market_id}: {e}")
                    continue
            
            self.logger.info(f"Ingested trades for {ingested_count} markets from {self.venue_name}")
            return ingested_count
            
        except Exception as e:
            self.logger.error(f"Error ingesting trades from {self.venue_name}: {e}")
            raise
    
    def _should_ingest_market(self, market: Dict[str, Any]) -> bool:
        """Determine if a market should be ingested based on resolution date."""
        resolution_date = market.get('resolution_date')
        if not resolution_date:
            return False
        
        # Convert to datetime if it's a string
        if isinstance(resolution_date, str):
            try:
                resolution_date = datetime.fromisoformat(resolution_date.replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Invalid resolution date format: {resolution_date}")
                return False
        
        return self._is_within_resolution_window(resolution_date)
    
    def _parse_resolution_date(self, resolution_date_str: str) -> datetime:
        """Parse resolution date string to datetime object."""
        if isinstance(resolution_date_str, datetime):
            return resolution_date_str
        
        if isinstance(resolution_date_str, str):
            try:
                return datetime.fromisoformat(resolution_date_str.replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Invalid resolution date format: {resolution_date_str}")
                return None
        
        return None
    
    async def _persist_market(self, market: Dict[str, Any]):
        """Persist market data to the database."""
        # Check if market already exists
        existing = self.db.query(RulesText).filter(
            RulesText.venue_id == self.venue.id,
            RulesText.market_id == market['id']
        ).first()
        
        # Parse resolution date to datetime object
        parsed_resolution_date = self._parse_resolution_date(market.get('resolution_date'))
        
        if existing:
            # Update existing record
            existing.rules_text = market.get('rules_text', '')
            existing.resolution_date = parsed_resolution_date
            existing.market_status = market.get('status', 'active')
            existing.version = market.get('version', '1.0')
        else:
            # Create new record
            new_market = RulesText(
                venue_id=self.venue.id,
                market_id=market['id'],
                rules_text=market.get('rules_text', ''),
                resolution_date=parsed_resolution_date,
                market_status=market.get('status', 'active'),
                version=market.get('version', '1.0')
            )
            self.db.add(new_market)
        
        self.db.commit()
    
    async def _persist_order_book(self, market_id: str, order_book: Dict[str, Any]):
        """Persist order book data to the database."""
        # Clear existing book levels for this market
        self.db.query(BookLevels).filter(
            BookLevels.venue_id == self.venue.id,
            BookLevels.market_id == market_id
        ).delete()
        
        # Extract top 10 levels for each side
        for side in ['buy', 'sell']:
            levels = order_book.get(f'{side}s', [])[:10]  # Top 10 levels
            
            for i, level in enumerate(levels, 1):
                book_level = BookLevels(
                    venue_id=self.venue.id,
                    market_id=market_id,
                    side=side,
                    level=i,
                    price=float(level.get('price', 0)),
                    size=float(level.get('size', 0)),
                    timestamp=datetime.utcnow()
                )
                self.db.add(book_level)
        
        self.db.commit()
    
    async def _persist_trades(self, market_id: str, trades: List[Dict[str, Any]]):
        """Persist trade data to the database."""
        # Note: This is a placeholder. In a real implementation, you'd want to:
        # 1. Check for duplicate trades
        # 2. Handle trade updates/cancellations
        # 3. Store trade details in a separate trades table
        
        # For now, we'll just log the trades (only if there are trades to avoid noise)
        if trades:
            self.logger.info(f"Received {len(trades)} trades for market {market_id}")
        else:
            self.logger.debug(f"Received {len(trades)} trades for market {market_id}")
        
        # TODO: Implement trade persistence when trades table is available
        pass
    
    async def run_continuous_ingestion(self, interval_seconds: int = 60):
        """Run continuous data ingestion at specified intervals."""
        self.logger.info(f"Starting continuous ingestion for {self.venue_name} every {interval_seconds} seconds")
        
        while True:
            try:
                # Ingest all data types
                await self.ingest_markets()
                await self.ingest_order_books()
                await self.ingest_trades()
                
                # Wait for next cycle
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in continuous ingestion for {self.venue_name}: {e}")
                await asyncio.sleep(interval_seconds)  # Continue despite errors
