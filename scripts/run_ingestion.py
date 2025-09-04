#!/usr/bin/env python3
"""
CLI script for running data ingestion services.
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.services.ingestion_manager import DataIngestionManager, create_ingestion_manager
from app.models.venue import Venue


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('ingestion.log')
        ]
    )


async def run_market_discovery(venue_names: list = None):
    """Run market discovery for specified venues."""
    db = next(get_db())
    try:
        manager = create_ingestion_manager(db)
        
        print(f"Starting market discovery for venues: {venue_names or 'all'}")
        results = await manager.run_market_discovery(venue_names)
        
        print("\nMarket Discovery Results:")
        for venue, result in results.items():
            if result == 1:
                print(f"  ✅ {venue}: Success")
            elif result == 0:
                print(f"  ❌ {venue}: Failed")
            else:
                print(f"  ⚠️  {venue}: Not available")
                
    except Exception as e:
        print(f"Error during market discovery: {e}")
        raise
    finally:
        db.close()


async def run_data_ingestion(venue_names: list = None):
    """Run data ingestion for specified venues."""
    db = next(get_db())
    try:
        manager = create_ingestion_manager(db)
        
        print(f"Starting data ingestion for venues: {venue_names or 'all'}")
        results = await manager.ingest_all_data(venue_names)
        
        print("\nData Ingestion Results:")
        for venue, venue_results in results.items():
            print(f"\n  📊 {venue}:")
            if 'error' in venue_results:
                print(f"    ❌ Error: {venue_results['error']}")
            else:
                print(f"    ✅ Markets: {venue_results['markets']}")
                print(f"    ✅ Order Books: {venue_results['order_books']}")
                print(f"    ✅ Trades: {venue_results['trades']}")
                
    except Exception as e:
        print(f"Error during data ingestion: {e}")
        raise
    finally:
        db.close()


async def run_continuous_ingestion(venue_names: list = None, interval: int = 60):
    """Run continuous data ingestion."""
    db = next(get_db())
    try:
        manager = create_ingestion_manager(db)
        manager.ingestion_interval = interval
        
        print(f"Starting continuous ingestion for venues: {venue_names or 'all'}")
        print(f"Ingestion interval: {interval} seconds")
        print("Press Ctrl+C to stop...")
        
        await manager.run_continuous_ingestion(venue_names)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping continuous ingestion...")
        manager.stop_all_ingestion()
        print("Continuous ingestion stopped.")
    except Exception as e:
        print(f"Error during continuous ingestion: {e}")
        raise
    finally:
        db.close()


async def show_status():
    """Show ingestion service status."""
    db = next(get_db())
    try:
        manager = create_ingestion_manager(db)
        status = await manager.get_ingestion_status()
        
        print("\n📊 Ingestion Service Status:")
        print(f"  Active Readers: {', '.join(status['active_readers']) if status['active_readers'] else 'None'}")
        print(f"  Total Venues: {status['total_venues']}")
        print(f"  Ingestion Interval: {status['ingestion_interval']} seconds")
        
        print("\n  Venue Details:")
        for venue_name, venue_status in status['venue_status'].items():
            print(f"    📍 {venue_name}:")
            if venue_status.get('active'):
                print(f"      ✅ Active")
                print(f"      📈 Markets: {venue_status.get('markets_count', 0)}")
                print(f"      📊 Order Books: {venue_status.get('order_books_count', 0)}")
            else:
                print(f"      ❌ Inactive")
                if 'error' in venue_status:
                    print(f"      🚨 Error: {venue_status['error']}")
                    
    except Exception as e:
        print(f"Error getting status: {e}")
        raise
    finally:
        db.close()


async def list_venues():
    """List available venues."""
    db = next(get_db())
    try:
        venues = db.query(Venue).filter(Venue.is_active == True).all()
        
        print("\n🏢 Available Venues:")
        for venue in venues:
            print(f"  📍 {venue.name} ({venue.display_name})")
            print(f"      Type: {venue.venue_type}")
            print(f"      Active: {'✅' if venue.is_active else '❌'}")
            if venue.description:
                print(f"      Description: {venue.description}")
            print()
            
    except Exception as e:
        print(f"Error listing venues: {e}")
        raise
    finally:
        db.close()


async def test_connection(venue_name: str):
    """Test connection to a specific venue."""
    db = next(get_db())
    try:
        manager = create_ingestion_manager(db)
        
        if venue_name not in manager.readers:
            print(f"❌ No reader available for venue: {venue_name}")
            return
        
        reader = manager.readers[venue_name]
        print(f"🔌 Testing connection to {venue_name}...")
        
        # Test with a simple API call
        if hasattr(reader, 'fetch_markets'):
            markets = await reader.fetch_markets()
            print(f"✅ Successfully connected to {venue_name}")
            print(f"   Found {len(markets)} markets")
        else:
            print(f"⚠️  Reader for {venue_name} doesn't support market fetching")
            
    except Exception as e:
        print(f"❌ Connection test failed for {venue_name}: {e}")
        raise
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Data Ingestion CLI")
    parser.add_argument("command", choices=[
        "discover", "ingest", "continuous", "status", "venues", "test"
    ], help="Command to execute")
    
    parser.add_argument("--venues", nargs="+", help="Specific venues to operate on")
    parser.add_argument("--interval", type=int, default=60, help="Ingestion interval in seconds (for continuous mode)")
    parser.add_argument("--venue-name", help="Venue name for connection testing")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Validate arguments
    if args.command == "test" and not args.venue_name:
        parser.error("--venue-name is required for test command")
    
    try:
        if args.command == "discover":
            asyncio.run(run_market_discovery(args.venues))
        elif args.command == "ingest":
            asyncio.run(run_data_ingestion(args.venues))
        elif args.command == "continuous":
            asyncio.run(run_continuous_ingestion(args.venues, args.interval))
        elif args.command == "status":
            asyncio.run(show_status())
        elif args.command == "venues":
            asyncio.run(list_venues())
        elif args.command == "test":
            asyncio.run(test_connection(args.venue_name))
            
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
