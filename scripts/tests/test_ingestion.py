#!/usr/bin/env python3
"""
Test script for data ingestion services.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db, create_tables
from app.services.ingestion_manager import create_ingestion_manager
from app.models.venue import Venue


async def test_ingestion_services():
    """Test the data ingestion services."""
    print("🧪 Testing data ingestion services...")
    
    # Create tables and seed venues
    create_tables()
    
    # Seed venues if they don't exist
    db = next(get_db())
    try:
        venues = db.query(Venue).all()
        if not venues:
            print("No venues found. Please run scripts/seed_venues.py first.")
            return
        
        print(f"Found {len(venues)} venues:")
        for venue in venues:
            print(f"  - {venue.name}: {venue.display_name}")
        
        # Test ingestion manager creation
        print("\n🔧 Testing ingestion manager creation...")
        manager = create_ingestion_manager(db)
        print(f"✅ Manager created with {len(manager.readers)} readers")
        
        # Test status endpoint
        print("\n📊 Testing status endpoint...")
        status = await manager.get_ingestion_status()
        print(f"✅ Status retrieved: {status['total_venues']} venues")
        
        # Test venue listing
        print("\n🏢 Testing venue listing...")
        for venue_name, reader in manager.readers.items():
            print(f"  - {venue_name}: {type(reader).__name__}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        db.close()


def main():
    """Main test function."""
    try:
        asyncio.run(test_ingestion_services())
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
