#!/usr/bin/env python3
"""
Debug script to see what's happening with pair creation
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.market_vectorizer import market_vectorizer
from app.services.equivalence_llm import equivalence_llm_service


async def debug_pairs():
    """Debug pair creation process."""
    print("🔍 Debugging pair creation process...")
    
    # Get all canonical markets
    all_markets = await market_vectorizer.get_all_canonical_markets()
    print(f"📊 Total markets: {len(all_markets)}")
    
    # Find similar pairs with vectorization
    similar_pairs = await market_vectorizer.find_all_similar_pairs(
        all_markets,
        threshold=0.5,
        max_pairs_per_market=10
    )
    
    print(f"🔗 Vectorization found {len(similar_pairs)} similar pairs")
    
    if not similar_pairs:
        print("❌ No similar pairs found by vectorization")
        return
    
    # Test LLM analysis on the first few pairs
    print("\n🧪 Testing LLM analysis on top pairs:")
    
    for i, (vector1, vector2, similarity) in enumerate(similar_pairs[:3], 1):
        print(f"\n--- Pair {i} ---")
        print(f"Vectorization similarity: {similarity:.3f}")
        print(f"Market 1: {vector1.canonical_id} ({vector1.venue_name})")
        print(f"Market 2: {vector2.canonical_id} ({vector2.venue_name})")
        
        # Get the actual market objects
        market1 = next(m for m in all_markets if m.id == vector1.market_id)
        market2 = next(m for m in all_markets if m.id == vector2.market_id)
        
        print(f"Market 1 question: {market1.question_text[:100]}...")
        print(f"Market 2 question: {market2.question_text[:100]}...")
        
        # Test LLM analysis
        try:
            analysis = await equivalence_llm_service.analyze_equivalence(market1, market2)
            print(f"LLM equivalence score: {analysis['equivalence_score']:.3f}")
            print(f"LLM hard_ok: {analysis['hard_ok']}")
            print(f"LLM confidence: {analysis['confidence']:.3f}")
            print(f"LLM conflicts: {analysis['conflict_list']}")
            
            if analysis['equivalence_score'] < 0.5:
                print("❌ LLM score too low for pair creation")
            else:
                print("✅ LLM score high enough for pair creation")
                
        except Exception as e:
            print(f"❌ LLM analysis failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_pairs())
