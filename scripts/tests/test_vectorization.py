#!/usr/bin/env python3
"""
Test script for market vectorization functionality.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.market_vectorizer import market_vectorizer
from app.database import get_db
from app.models.canonical_market import CanonicalMarket


async def test_vectorization():
    """Test the vectorization functionality."""
    print("🔍 Testing Market Vectorization...")
    
    try:
        # Get a few canonical markets for testing
        db = next(get_db())
        markets = db.query(CanonicalMarket).limit(5).all()
        db.close()
        
        if not markets:
            print("❌ No canonical markets found. Run normalization first.")
            return
        
        print(f"📊 Found {len(markets)} markets to test")
        
        # Test vectorization
        print("🔄 Vectorizing markets...")
        vectors = await market_vectorizer.vectorize_markets_batch(markets)
        print(f"✅ Vectorized {len(vectors)} markets")
        
        # Test similarity search
        if len(vectors) >= 2:
            print("🔍 Testing similarity search...")
            target_vector = vectors[0]
            similar_markets = await market_vectorizer.find_similar_markets(
                target_vector, 
                vectors[1:], 
                threshold=0.5,
                max_results=3
            )
            
            print(f"📈 Found {len(similar_markets)} similar markets for '{target_vector.question_text[:50]}...'")
            for similar_vector, similarity in similar_markets:
                print(f"  - {similarity:.3f}: {similar_vector.question_text[:50]}...")
        
        # Test pair finding
        print("🔗 Testing pair finding...")
        similar_pairs = await market_vectorizer.find_all_similar_pairs(
            markets,
            threshold=0.5,
            max_pairs_per_market=2
        )
        
        print(f"🎯 Found {len(similar_pairs)} similar market pairs")
        for vector1, vector2, similarity in similar_pairs:
            print(f"  - {similarity:.3f}: {vector1.question_text[:30]}... <-> {vector2.question_text[:30]}...")
        
        print("✅ Vectorization test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during vectorization test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vectorization())
