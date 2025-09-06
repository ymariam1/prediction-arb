#!/usr/bin/env python3
"""
Mock Test for Market Normalization Pipeline

This script tests the normalization pipeline with mock LLM responses
to demonstrate the system without requiring actual API keys.
"""

import asyncio
import sys
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/Users/yohannesmariam/Developer/projects/prediction-arb')

from app.services.canonizer import CanonizerService
from app.services.equivalence_llm import EquivalenceLLMService
from app.database import get_db
from app.models.rules_text import RulesText
from app.models.canonical_market import CanonicalMarket


class MockCanonizerService(CanonizerService):
    """Mock canonizer service for testing."""
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Mock LLM call that returns a realistic response."""
        # Mock response for market normalization
        mock_response = {
            "question_text": "Will the S&P 500 close above 4500 on December 31, 2024?",
            "outcome_options": ["Yes", "No"],
            "resolution_criteria": {
                "description": "Market will resolve based on the closing price of the S&P 500 on December 31, 2024",
                "deadline": "December 31, 2024 at market close",
                "authority": "Market data provider (e.g., Yahoo Finance, Bloomberg)"
            },
            "category": "financial",
            "tags": ["stocks", "S&P 500", "2024", "year-end"]
        }
        return json.dumps(mock_response)


class MockEquivalenceLLMService(EquivalenceLLMService):
    """Mock equivalence LLM service for testing."""
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Mock LLM call that returns a realistic equivalence analysis."""
        # Mock response for equivalence analysis
        mock_response = {
            "equivalence_score": 0.95,
            "hard_ok": True,
            "confidence": 0.9,
            "conflict_list": [],
            "reasoning": "Both markets ask the same question about S&P 500 closing above 4500 on the same date. The resolution criteria are identical and both use standard market data sources."
        }
        return json.dumps(mock_response)


async def test_normalization():
    """Test the normalization pipeline with mock services."""
    print("🧪 Testing Market Normalization Pipeline with Mock LLM...")
    
    # Get a sample rules text record
    db = next(get_db())
    sample_rules = db.query(RulesText).first()
    
    if not sample_rules:
        print("❌ No rules text records found. Run market discovery first.")
        db.close()
        return
    
    # Access venue name while session is open
    venue_name = sample_rules.venue.name
    db.close()
    
    print(f"📝 Testing with market: {sample_rules.market_id} from {venue_name}")
    print(f"📄 Rules text preview: {sample_rules.rules_text[:100]}...")
    
    # Test canonizer
    print("\n🔄 Testing Canonizer Service...")
    mock_canonizer = MockCanonizerService()
    
    canonical_market = await mock_canonizer.normalize_market(sample_rules)
    
    if canonical_market:
        print(f"✅ Canonical market created: {canonical_market.canonical_id}")
        print(f"   Question: {canonical_market.question_text}")
        print(f"   Outcomes: {canonical_market.outcome_options}")
        print(f"   Category: {canonical_market.category}")
        print(f"   Tags: {canonical_market.tags}")
    else:
        print("❌ Failed to create canonical market")
        return
    
    # Test equivalence analysis
    print("\n🔍 Testing Equivalence LLM Service...")
    mock_equivalence = MockEquivalenceLLMService()
    
    # Get another market for comparison
    db = next(get_db())
    other_rules = db.query(RulesText).filter(RulesText.id != sample_rules.id).first()
    db.close()
    
    if other_rules:
        # Normalize the other market too
        other_canonical = await mock_canonizer.normalize_market(other_rules)
        
        if other_canonical:
            print(f"📝 Comparing with market: {other_canonical.canonical_id}")
            
            # Test equivalence analysis
            analysis = await mock_equivalence.analyze_equivalence(canonical_market, other_canonical)
            
            print(f"✅ Equivalence analysis completed:")
            print(f"   Score: {analysis['equivalence_score']}")
            print(f"   Hard OK: {analysis['hard_ok']}")
            print(f"   Confidence: {analysis['confidence']}")
            print(f"   Conflicts: {analysis['conflict_list']}")
            print(f"   Reasoning: {analysis['reasoning'][:100]}...")
            
            # Test pair creation
            if analysis['equivalence_score'] >= 0.7:
                print("\n🔗 Testing Pair Creation...")
                pair = await mock_equivalence.create_pair(canonical_market, other_canonical)
                
                if pair:
                    print(f"✅ Pair created successfully:")
                    print(f"   Market A: {pair.market_a.canonical_id}")
                    print(f"   Market B: {pair.market_b.canonical_id}")
                    print(f"   Equivalence Score: {pair.equivalence_score}")
                    print(f"   Status: {pair.status}")
                else:
                    print("❌ Failed to create pair")
            else:
                print(f"⏭️  Skipping pair creation (score {analysis['equivalence_score']} < 0.7)")
        else:
            print("❌ Failed to normalize second market")
    else:
        print("⚠️  Only one market available for testing")
    
    print("\n✅ Mock normalization test completed successfully!")


async def show_test_results():
    """Show the results of the test."""
    print("\n📊 Test Results:")
    
    db = next(get_db())
    
    # Count canonical markets
    canonical_count = db.query(CanonicalMarket).count()
    print(f"   Canonical Markets: {canonical_count}")
    
    # Count pairs
    from app.models.pairs import Pairs
    pairs_count = db.query(Pairs).count()
    print(f"   Pairs: {pairs_count}")
    
    if pairs_count > 0:
        pairs = db.query(Pairs).all()
        for pair in pairs:
            print(f"   - {pair.market_a.canonical_id} ↔ {pair.market_b.canonical_id} (score: {pair.equivalence_score})")
    
    db.close()


def main():
    """Main entry point."""
    try:
        asyncio.run(test_normalization())
        asyncio.run(show_test_results())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
