#!/usr/bin/env python3
"""
Simple test script for database functionality.
"""

import os
import sys
sys.path.append('.')

# Set environment variable to force SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Create SQLite engine
engine = create_engine('sqlite:///./test.db', echo=True)

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Database connection successful!")
    print("Test query result:", result.fetchone())

# Clean up
os.remove('./test.db')
print("Test completed successfully!")
