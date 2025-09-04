"""
Data ingestion manager for coordinating venue data ingestion services.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.kalshi_reader import KalshiReader
from app.services.poly_reader import PolyReader
from app.models.venue import Venue


class DataIngestionManager:
    """Manages data ingestion from multiple venues."""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize venue readers
        self.readers: Dict[str, Any] = {}
        self._initialize_readers()
        
        # Ingestion configuration
        self.ingestion_interval = 60  # seconds
        self.max_concurrent_ingestions = 3
        
    def _initialize_readers(self):
        """Initialize venue readers for available venues."""
        try:
            # Get all active venues from database
            venues = self.db.query(Venue).filter(Venue.is_active == True).all()
            
            for venue in venues:
                if venue.name.lower() == "kalshi":
                    self.readers["kalshi"] = KalshiReader(self.db)
                    self.logger.info("Initialized Kalshi reader")
                elif venue.name.lower() == "polymarket":
                    self.readers["polymarket"] = PolyReader(self.db)
                    self.logger.info("Initialized Polymarket reader")
                else:
                    self.logger.warning(f"Unknown venue type: {venue.name}")
                    
        except Exception as e:
            self.logger.error(f"Error initializing venue readers: {e}")
            raise
    
    async def run_market_discovery(self, venue_names: Optional[List[str]] = None) -> Dict[str, int]:
        """Run market discovery for specified venues or all venues."""
        if venue_names is None:
            venue_names = list(self.readers.keys())
        
        results = {}
        
        for venue_name in venue_names:
            if venue_name in self.readers:
                try:
                    self.logger.info(f"Starting market discovery for {venue_name}")
                    await self.readers[venue_name].run_market_discovery()
                    results[venue_name] = 1  # Success
                except Exception as e:
                    self.logger.error(f"Market discovery failed for {venue_name}: {e}")
                    results[venue_name] = 0  # Failure
            else:
                self.logger.warning(f"No reader available for venue: {venue_name}")
                results[venue_name] = -1  # Not available
        
        return results
    
    async def ingest_all_data(self, venue_names: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
        """Ingest all data types from specified venues or all venues."""
        if venue_names is None:
            venue_names = list(self.readers.keys())
        
        results = {}
        
        for venue_name in venue_names:
            if venue_name in self.readers:
                try:
                    reader = self.readers[venue_name]
                    
                    # Ingest markets, order books, and trades
                    markets_count = await reader.ingest_markets()
                    order_books_count = await reader.ingest_order_books()
                    trades_count = await reader.ingest_trades()
                    
                    results[venue_name] = {
                        'markets': markets_count,
                        'order_books': order_books_count,
                        'trades': trades_count
                    }
                    
                    self.logger.info(f"Data ingestion completed for {venue_name}: "
                                   f"{markets_count} markets, {order_books_count} order books, {trades_count} trades")
                    
                except Exception as e:
                    self.logger.error(f"Data ingestion failed for {venue_name}: {e}")
                    results[venue_name] = {
                        'markets': 0,
                        'order_books': 0,
                        'trades': 0,
                        'error': str(e)
                    }
            else:
                self.logger.warning(f"No reader available for venue: {venue_name}")
                results[venue_name] = {
                    'markets': -1,
                    'order_books': -1,
                    'trades': -1,
                    'error': 'Reader not available'
                }
        
        return results
    
    async def run_continuous_ingestion(self, venue_names: Optional[List[str]] = None):
        """Run continuous data ingestion for specified venues."""
        if venue_names is None:
            venue_names = list(self.readers.keys())
        
        self.logger.info(f"Starting continuous ingestion for venues: {venue_names}")
        
        # Create tasks for each venue
        tasks = []
        for venue_name in venue_names:
            if venue_name in self.readers:
                task = asyncio.create_task(
                    self.readers[venue_name].run_continuous_ingestion(self.ingestion_interval)
                )
                tasks.append(task)
                self.logger.info(f"Started continuous ingestion for {venue_name}")
        
        if not tasks:
            self.logger.warning("No valid readers available for continuous ingestion")
            return
        
        # Wait for all tasks to complete (they run indefinitely)
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in continuous ingestion: {e}")
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            raise
    
    async def run_single_ingestion_cycle(self, venue_names: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
        """Run a single ingestion cycle for all data types."""
        return await self.ingest_all_data(venue_names)
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get the current status of all ingestion services."""
        status = {
            'active_readers': list(self.readers.keys()),
            'total_venues': len(self.readers),
            'ingestion_interval': self.ingestion_interval,
            'last_ingestion': None,  # TODO: Track last ingestion time
            'venue_status': {}
        }
        
        # Get status for each venue
        for venue_name, reader in self.readers.items():
            try:
                # Check if venue is accessible
                venue_status = {
                    'name': venue_name,
                    'active': True,
                    'last_success': None,  # TODO: Track last successful ingestion
                    'error_count': 0,  # TODO: Track error count
                    'markets_count': 0,
                    'order_books_count': 0
                }
                
                # Get counts from database
                from app.models.rules_text import RulesText
                from app.models.book_levels import BookLevels
                
                venue_id = reader.venue.id
                venue_status['markets_count'] = self.db.query(RulesText).filter(
                    RulesText.venue_id == venue_id
                ).count()
                
                venue_status['order_books_count'] = self.db.query(BookLevels).filter(
                    BookLevels.venue_id == venue_id
                ).count()
                
                status['venue_status'][venue_name] = venue_status
                
            except Exception as e:
                self.logger.error(f"Error getting status for venue {venue_name}: {e}")
                status['venue_status'][venue_name] = {
                    'name': venue_name,
                    'active': False,
                    'error': str(e)
                }
        
        return status
    
    def stop_all_ingestion(self):
        """Stop all running ingestion services."""
        self.logger.info("Stopping all ingestion services")
        # TODO: Implement graceful shutdown of continuous ingestion tasks
        pass


# Factory function for creating ingestion manager
def create_ingestion_manager(db: Session) -> DataIngestionManager:
    """Create and return a new data ingestion manager instance."""
    return DataIngestionManager(db)


# Async context manager for running ingestion
class IngestionContext:
    """Context manager for running data ingestion."""
    
    def __init__(self, db: Session):
        self.db = db
        self.manager = None
    
    async def __aenter__(self):
        self.manager = create_ingestion_manager(self.db)
        return self.manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.manager:
            self.manager.stop_all_ingestion()
