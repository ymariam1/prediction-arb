#!/usr/bin/env python3
"""
Script to find market pairs with different similarity thresholds
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalization_pipeline import normalization_pipeline
from app.services.market_vectorizer import market_vectorizer


async def find_pairs_with_threshold(threshold: float):
    """Find pairs with a specific similarity threshold."""
    print(f"\n🔍 Finding pairs with similarity threshold: {threshold}")
    
    # Get all canonical markets
    all_markets = await market_vectorizer.get_all_canonical_markets()
    print(f"📊 Total markets: {len(all_markets)}")
    
    # Find similar pairs
    similar_pairs = await market_vectorizer.find_all_similar_pairs(
        all_markets,
        threshold=threshold,
        max_pairs_per_market=10
    )
    
    print(f"🔗 Found {len(similar_pairs)} similar pairs above threshold {threshold}")
    
    if similar_pairs:
        print("\nTop 5 pairs:")
        for i, (vector1, vector2, similarity) in enumerate(similar_pairs[:5], 1):
            print(f"  {i}. {vector1.canonical_id} ↔ {vector2.canonical_id}")
            print(f"     Similarity: {similarity:.3f}")
            print(f"     Venues: {vector1.venue_name} ↔ {vector2.venue_name}")
            print()
    
    return similar_pairs


async def main():
    """Test different similarity thresholds."""
    print("🚀 Testing different similarity thresholds for pair finding")
    
    thresholds = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    
    for threshold in thresholds:
        pairs = await find_pairs_with_threshold(threshold)
        if pairs:
            print(f"✅ Threshold {threshold}: Found {len(pairs)} pairs")
            break
        else:
            print(f"❌ Threshold {threshold}: No pairs found")
    
    print("\n🎯 Recommendation: Use the lowest threshold that finds pairs for initial testing")


if __name__ == "__main__":
    asyncio.run(main())
