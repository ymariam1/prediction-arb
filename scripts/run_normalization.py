#!/usr/bin/env python3
"""
Market Normalization Pipeline Runner

This script runs the market normalization and pair matching pipeline.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/Users/yohannesmariam/Developer/projects/prediction-arb')

from app.services.normalization_pipeline import normalization_pipeline
from app.services.canonizer import canonizer_service
from app.services.equivalence_llm import equivalence_llm_service
from app.database import get_db
from app.models.canonical_market import CanonicalMarket
from app.models.pairs import Pairs


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('normalization.log')
        ]
    )


async def run_full_pipeline(incremental=False, limit=None):
    """Run the complete normalization pipeline."""
    mode = "incremental" if incremental else "full"
    print(f"🚀 Starting {mode} market normalization pipeline...")
    
    results = await normalization_pipeline.run_full_pipeline(incremental=incremental, limit=limit)
    
    print(f"\n✅ Pipeline completed in {results['duration']:.2f} seconds")
    print(f"📊 Created {results['canonical_markets_created']} canonical markets")
    print(f"🔗 Created {results['pairs_created']} pairs")
    
    if results['errors']:
        print(f"❌ Errors encountered: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   - {error}")
    
    return results


async def normalize_pending():
    """Normalize all pending markets."""
    print("🔄 Normalizing pending markets...")
    
    canonical_markets = await canonizer_service.normalize_all_pending_markets()
    
    print(f"✅ Normalized {len(canonical_markets)} markets")
    return canonical_markets


async def find_pairs():
    """Find potential pairs."""
    print("🔍 Finding potential pairs...")
    
    pairs = await equivalence_llm_service.find_all_potential_pairs()
    
    print(f"✅ Found {len(pairs)} potential pairs")
    return pairs


async def show_status():
    """Show pipeline status."""
    print("📊 Pipeline Status:")
    
    status = await normalization_pipeline.get_pipeline_status()
    
    print(f"   Total Rules Text: {status['total_rules_text']}")
    print(f"   Total Canonical Markets: {status['total_canonical_markets']}")
    print(f"   Normalization Coverage: {status['normalization_coverage']:.1%}")
    print(f"   Total Pairs: {status['total_pairs']}")
    print(f"   Active Pairs: {status['active_pairs']}")
    print(f"   High Confidence Pairs (≥0.9): {status['high_confidence_pairs']}")
    print(f"   Medium Confidence Pairs (0.7-0.9): {status['medium_confidence_pairs']}")
    print(f"   Low Confidence Pairs (<0.7): {status['low_confidence_pairs']}")
    
    # Show normalization progress details
    if 'normalization_progress' in status:
        progress = status['normalization_progress']
        print(f"\n📈 Normalization Progress:")
        print(f"   Pending Markets: {progress['pending_markets']}")
        print(f"   Recent Rules (7 days): {progress['recent_rules_7_days']}")
        print(f"   Normalization %: {progress['normalization_percentage']:.1f}%")


async def show_pairs(limit: int = 10):
    """Show recent pairs."""
    print(f"🔗 Recent Pairs (limit: {limit}):")
    
    db = next(get_db())
    pairs = db.query(Pairs).order_by(Pairs.created_at.desc()).limit(limit).all()
    db.close()
    
    if not pairs:
        print("   No pairs found")
        return
    
    for pair in pairs:
        print(f"   {pair.market_a.canonical_id} ↔ {pair.market_b.canonical_id}")
        print(f"      Score: {pair.equivalence_score:.3f}, Confidence: {pair.confidence:.3f}")
        print(f"      Hard OK: {pair.hard_ok}, Status: {pair.status}")
        if pair.conflict_list:
            print(f"      Conflicts: {', '.join(pair.conflict_list[:2])}")
        print()


async def test_llm():
    """Test LLM connectivity."""
    print("🧪 Testing LLM connectivity...")
    
    try:
        # Test with a simple prompt
        response = await canonizer_service._call_llm(
            "What is 2+2?",
            "You are a helpful assistant. Answer briefly."
        )
        print(f"✅ LLM test successful: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False


async def cleanup_pairs(days: int = 30):
    """Clean up inactive pairs."""
    print(f"🧹 Cleaning up pairs inactive for {days} days...")
    
    cleaned = await normalization_pipeline.cleanup_inactive_pairs(days)
    
    print(f"✅ Marked {cleaned} pairs as inactive")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Market Normalization Pipeline")
    parser.add_argument("command", choices=[
        "run", "run-incremental", "normalize", "pairs", "status", "show-pairs", "test-llm", "cleanup"
    ], help="Command to run")
    parser.add_argument("--limit", type=int, default=10, help="Limit for show-pairs or incremental run")
    parser.add_argument("--days", type=int, default=30, help="Days threshold for cleanup command")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    try:
        if args.command == "run":
            asyncio.run(run_full_pipeline())
        elif args.command == "run-incremental":
            asyncio.run(run_full_pipeline(incremental=True, limit=args.limit))
        elif args.command == "normalize":
            asyncio.run(normalize_pending())
        elif args.command == "pairs":
            asyncio.run(find_pairs())
        elif args.command == "status":
            asyncio.run(show_status())
        elif args.command == "show-pairs":
            asyncio.run(show_pairs(args.limit))
        elif args.command == "test-llm":
            asyncio.run(test_llm())
        elif args.command == "cleanup":
            asyncio.run(cleanup_pairs(args.days))
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
