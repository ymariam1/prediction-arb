#!/usr/bin/env python3
"""
Database initialization script for local development.
This script sets up the database with initial data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, create_tables, SessionLocal
from app.models import Venue, User
from app.config import settings
import uuid


def init_venues():
    """Initialize venue data."""
    db = SessionLocal()
    try:
        # Check if venues already exist
        existing_venues = db.query(Venue).count()
        if existing_venues > 0:
            print("Venues already exist, skipping initialization.")
            return
        
        # Create initial venues
        venues = [
            Venue(
                name="kalshi",
                display_name="Kalshi",
                api_base_url="https://trading-api.kalshi.com",
                venue_type="prediction_market",
                description="Kalshi prediction market platform"
            ),
            Venue(
                name="polymarket",
                display_name="Polymarket",
                api_base_url="https://clob.polymarket.com",
                venue_type="prediction_market", 
                description="Polymarket prediction market platform"
            )
        ]
        
        db.add_all(venues)
        db.commit()
        print(f"Created {len(venues)} venues")
        
    except Exception as e:
        print(f"Error creating venues: {e}")
        db.rollback()
    finally:
        db.close()


def init_users():
    """Initialize test user data."""
    db = SessionLocal()
    try:
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Users already exist, skipping initialization.")
            return
        
        # Create test user (password: test123)
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        test_user = User(
            email="test@example.com",
            username="testuser",
            password_hash=pwd_context.hash("test123"),
            is_active=True,
            is_verified=True,
            role="admin"
        )
        
        db.add(test_user)
        db.commit()
        print("Created test user: test@example.com / test123")
        
    except Exception as e:
        print(f"Error creating users: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function."""
    print("Initializing database...")
    
    # Create tables
    create_tables()
    print("Database tables created")
    
    # Initialize data
    init_venues()
    init_users()
    
    print("Database initialization complete!")


if __name__ == "__main__":
    main()
