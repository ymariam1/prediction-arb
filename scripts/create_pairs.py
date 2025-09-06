#!/usr/bin/env python3
"""
Script to create market pairs for testing
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalization_pipeline import normalization_pipeline


async def create_pairs():
    """Create market pairs for testing."""
    print("🔗 Creating market pairs for testing...")
    
    # Run pair creation with threshold 0.5
    pairs = await normalization_pipeline.find_and_create_pairs(similarity_threshold=0.5)
    
    print(f"✅ Created {len(pairs)} market pairs")
    
    if pairs:
        print("\nCreated pairs:")
        for i, pair in enumerate(pairs, 1):
            print(f"  {i}. {pair.market_a.canonical_id} ↔ {pair.market_b.canonical_id}")
            print(f"     Equivalence Score: {pair.equivalence_score:.3f}")
            print(f"     Confidence: {pair.confidence:.3f}")
            print(f"     Hard OK: {pair.hard_ok}")
            print()
    
    return pairs


if __name__ == "__main__":
    asyncio.run(create_pairs())
