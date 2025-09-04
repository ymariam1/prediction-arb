#!/usr/bin/env python3
"""
Simple script to create database tables.
"""

import os
import sys
sys.path.append('.')

# Set environment variable to force SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./prediction_arb.db'

from sqlalchemy import create_engine, text
from app.models import Base

# Create SQLite engine
engine = create_engine('sqlite:///./prediction_arb.db', echo=True)

# Create all tables
Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = result.fetchall()
    print(f"Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
