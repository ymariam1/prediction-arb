"""
API endpoints for data ingestion operations.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from app.database import get_db
from app.services.ingestion_manager import DataIngestionManager, create_ingestion_manager
from app.models.venue import Venue

router = APIRouter(prefix="/api/v1/ingestion", tags=["Data Ingestion"])

logger = logging.getLogger(__name__)


@router.post("/discover-markets")
async def discover_markets(
    venue_names: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Run market discovery for specified venues or all venues.
    
    This endpoint will:
    1. Fetch all available markets from the specified venues
    2. Filter for markets resolving within 7 days
    3. Store market data in the database
    4. Optionally run in background if specified
    """
    try:
        manager = create_ingestion_manager(db)
        
        if background_tasks:
            # Run in background
            background_tasks.add_task(manager.run_market_discovery, venue_names)
            return {
                "message": "Market discovery started in background",
                "venues": venue_names or list(manager.readers.keys())
            }
        else:
            # Run synchronously
            results = await manager.run_market_discovery(venue_names)
            return {
                "message": "Market discovery completed",
                "results": results
            }
            
    except Exception as e:
        logger.error(f"Error in market discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Market discovery failed: {str(e)}")


@router.post("/ingest-data")
async def ingest_data(
    venue_names: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Ingest all data types (markets, order books, trades) from specified venues.
    
    This endpoint will:
    1. Fetch and store market data
    2. Fetch and store order book data (top 10 levels)
    3. Fetch and store trade data
    4. Optionally run in background if specified
    """
    try:
        manager = create_ingestion_manager(db)
        
        if background_tasks:
            # Run in background
            background_tasks.add_task(manager.ingest_all_data, venue_names)
            return {
                "message": "Data ingestion started in background",
                "venues": venue_names or list(manager.readers.keys())
            }
        else:
            # Run synchronously
            results = await manager.ingest_all_data(venue_names)
            return {
                "message": "Data ingestion completed",
                "results": results
            }
            
    except Exception as e:
        logger.error(f"Error in data ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")


@router.post("/start-onchain-listeners")
async def start_onchain_listeners(
    venue_names: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Start on-chain event listeners for specified venues.
    
    This endpoint will:
    1. Connect to blockchain networks
    2. Listen for real-time events (trades, new markets, resolutions)
    3. Update database with real-time data
    4. Optionally run in background if specified
    """
    try:
        manager = create_ingestion_manager(db)
        
        if background_tasks:
            # Run in background
            background_tasks.add_task(manager.start_onchain_listeners, venue_names)
            return {
                "message": "On-chain listeners started in background",
                "venues": venue_names or ["polymarket"]
            }
        else:
            # Run synchronously (this will block)
            await manager.start_onchain_listeners(venue_names)
            return {
                "message": "On-chain listeners completed",
                "venues": venue_names or ["polymarket"]
            }
            
    except Exception as e:
        logger.error(f"Error starting on-chain listeners: {e}")
        raise HTTPException(status_code=500, detail=f"On-chain listeners failed: {str(e)}")


@router.post("/start-continuous")
async def start_continuous_ingestion(
    venue_names: Optional[List[str]] = None,
    interval_seconds: int = 60,
    db: Session = Depends(get_db)
):
    """
    Start continuous data ingestion for specified venues.
    
    This will run indefinitely, ingesting data at the specified interval.
    Use the stop endpoint to halt the process.
    """
    try:
        manager = create_ingestion_manager(db)
        
        # Set custom interval if provided
        if interval_seconds != 60:
            manager.ingestion_interval = interval_seconds
        
        # Start continuous ingestion in background
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(manager.run_continuous_ingestion(venue_names))
        
        return {
            "message": "Continuous ingestion started",
            "venues": venue_names or list(manager.readers.keys()),
            "interval_seconds": manager.ingestion_interval
        }
        
    except Exception as e:
        logger.error(f"Error starting continuous ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start continuous ingestion: {str(e)}")


@router.post("/stop-continuous")
async def stop_continuous_ingestion(db: Session = Depends(get_db)):
    """
    Stop all running continuous ingestion services.
    """
    try:
        manager = create_ingestion_manager(db)
        manager.stop_all_ingestion()
        
        return {
            "message": "Continuous ingestion stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping continuous ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop continuous ingestion: {str(e)}")


@router.get("/status")
async def get_ingestion_status(db: Session = Depends(get_db)):
    """
    Get the current status of all ingestion services.
    
    Returns information about:
    - Active readers
    - Venue status
    - Data counts
    - Last ingestion times
    """
    try:
        manager = create_ingestion_manager(db)
        status = await manager.get_ingestion_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion status: {str(e)}")


@router.get("/venues")
async def get_available_venues(db: Session = Depends(get_db)):
    """
    Get list of available venues for data ingestion.
    """
    try:
        venues = db.query(Venue).filter(Venue.is_active == True).all()
        
        venue_list = []
        for venue in venues:
            venue_info = {
                "id": str(venue.id),
                "name": venue.name,
                "display_name": venue.display_name,
                "venue_type": venue.venue_type,
                "is_active": venue.is_active,
                "description": venue.description
            }
            venue_list.append(venue_info)
        
        return {
            "venues": venue_list,
            "total": len(venue_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting venues: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get venues: {str(e)}")


@router.get("/health")
async def ingestion_health_check(db: Session = Depends(get_db)):
    """
    Health check for ingestion services.
    """
    try:
        manager = create_ingestion_manager(db)
        status = await manager.get_ingestion_status()
        
        # Check if we have any active readers
        healthy = len(status['active_readers']) > 0
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "active_readers": status['active_readers'],
            "total_venues": status['total_venues']
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/test-connection/{venue_name}")
async def test_venue_connection(
    venue_name: str,
    db: Session = Depends(get_db)
):
    """
    Test connection to a specific venue.
    
    This will attempt to make a simple API call to verify connectivity.
    """
    try:
        manager = create_ingestion_manager(db)
        
        if venue_name not in manager.readers:
            raise HTTPException(status_code=404, detail=f"No reader available for venue: {venue_name}")
        
        reader = manager.readers[venue_name]
        
        # Test with a simple API call
        if hasattr(reader, 'fetch_markets'):
            markets = await reader.fetch_markets()
            return {
                "venue": venue_name,
                "status": "connected",
                "markets_count": len(markets),
                "message": f"Successfully connected to {venue_name}"
            }
        else:
            return {
                "venue": venue_name,
                "status": "unknown",
                "message": f"Reader for {venue_name} doesn't support market fetching"
            }
            
    except Exception as e:
        logger.error(f"Connection test failed for {venue_name}: {e}")
        return {
            "venue": venue_name,
            "status": "failed",
            "error": str(e)
        }
