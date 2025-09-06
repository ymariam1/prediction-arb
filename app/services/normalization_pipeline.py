"""
Market Normalization Pipeline

This service orchestrates the complete market normalization and pair matching process.
It coordinates between the canonizer and equivalence-llm services.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from app.models.canonical_market import CanonicalMarket
from app.models.pairs import Pairs
from app.models.rules_text import RulesText
from app.database import get_db
from app.services.canonizer import canonizer_service
from app.services.equivalence_llm import equivalence_llm_service
from app.services.market_vectorizer import market_vectorizer


class NormalizationPipeline:
    """Pipeline for market normalization and pair matching."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def run_full_pipeline(self, incremental: bool = False, limit: int = None) -> Dict[str, Any]:
        """Run the complete normalization and pair matching pipeline."""
        self.logger.info(f"Starting {'incremental' if incremental else 'full'} market normalization pipeline")
        
        start_time = datetime.now()
        results = {
            "start_time": start_time,
            "canonical_markets_created": 0,
            "pairs_created": 0,
            "errors": [],
            "incremental": incremental,
            "limit": limit
        }
        
        try:
            # Step 1: Normalize markets (all pending or incremental)
            if incremental:
                self.logger.info(f"Step 1: Normalizing new markets only (limit: {limit})")
                canonical_markets = await canonizer_service.normalize_new_markets_only(limit)
            else:
                self.logger.info("Step 1: Normalizing all pending markets")
                canonical_markets = await canonizer_service.normalize_all_pending_markets()
            
            results["canonical_markets_created"] = len(canonical_markets)
            
            if not canonical_markets:
                self.logger.info("No new markets to normalize")
                end_time = datetime.now()
                results["end_time"] = end_time
                results["duration"] = (end_time - start_time).total_seconds()
                return results
            
            # Step 2: Find potential pairs using vectorization (only if we have new markets)
            if canonical_markets:
                self.logger.info("Step 2: Finding potential pairs using vectorization")
                pairs = await self.find_and_create_pairs(similarity_threshold=0.5)
                results["pairs_created"] = len(pairs)
                
                # Step 3: Update existing pairs with new markets
                self.logger.info("Step 3: Updating existing pairs with new markets")
                existing_pairs = await self._update_existing_pairs(canonical_markets)
                results["pairs_created"] += existing_pairs
            
            end_time = datetime.now()
            results["end_time"] = end_time
            results["duration"] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Pipeline completed successfully in {results['duration']:.2f} seconds")
            self.logger.info(f"Created {results['canonical_markets_created']} canonical markets and {results['pairs_created']} pairs")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            results["errors"].append(str(e))
            results["end_time"] = datetime.now()
            results["duration"] = (results["end_time"] - start_time).total_seconds()
        
        return results
    
    async def _update_existing_pairs(self, new_markets: List[CanonicalMarket]) -> int:
        """Update existing pairs with new markets using vectorization for efficiency."""
        if not new_markets:
            return 0
        
        self.logger.info(f"Finding pairs for {len(new_markets)} new markets using vectorization")
        
        # Get all existing markets for comparison
        all_markets = await market_vectorizer.get_all_canonical_markets()
        
        # Use vectorization to find similar pairs between new and existing markets
        similar_pairs = await market_vectorizer.find_similar_pairs_for_new_markets(
            new_markets,
            all_markets,
            threshold=0.5,  # Lowered threshold to find more pairs
            max_pairs_per_market=10  # Increased to find more pairs
        )
        
        if not similar_pairs:
            self.logger.info("No similar market pairs found for new markets")
            return 0
        
        self.logger.info(f"Found {len(similar_pairs)} similar pairs for new markets, analyzing with LLM")
        
        # Analyze similar pairs with LLM for equivalence
        pairs_created = 0
        db = next(get_db())
        
        try:
            for new_vector, existing_vector, similarity in similar_pairs:
                try:
                    # Get the actual CanonicalMarket objects
                    new_market = next(m for m in new_markets if m.id == new_vector.market_id)
                    existing_market = next(m for m in all_markets if m.id == existing_vector.market_id)
                    
                    # Skip if already paired
                    existing_pair = db.query(Pairs).filter(
                        ((Pairs.market_a_id == new_market.id) & (Pairs.market_b_id == existing_market.id)) |
                        ((Pairs.market_a_id == existing_market.id) & (Pairs.market_b_id == new_market.id))
                    ).first()
                    
                    if existing_pair:
                        continue
                    
                    # Analyze with LLM
                    pair_data = await equivalence_llm_service.analyze_equivalence(new_market, existing_market)
                    
                    if pair_data and pair_data.get("equivalence_score", 0) > 0.5:
                        pair = Pairs(**pair_data)
                        db.add(pair)
                        pairs_created += 1
                        self.logger.info(f"Created pair: {new_market.canonical_id} <-> {existing_market.canonical_id} (score: {pair_data.get('equivalence_score', 0):.2f})")
                    
                except Exception as e:
                    self.logger.error(f"Failed to analyze pair {new_vector.canonical_id} <-> {existing_vector.canonical_id}: {e}")
                    continue
            
            db.commit()
            self.logger.info(f"Created {pairs_created} pairs for new markets using vectorization + LLM")
            return pairs_created
            
        except Exception as e:
            self.logger.error(f"Error in _update_existing_pairs: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    async def find_and_create_pairs(self, similarity_threshold: float = 0.5) -> List[Pairs]:
        """Find and create market pairs using vectorization for efficiency."""
        db = next(get_db())
        
        try:
            # Get all canonical markets
            canonical_markets = await market_vectorizer.get_all_canonical_markets()
            
            if len(canonical_markets) < 2:
                self.logger.info("Not enough markets to create pairs")
                return []
            
            # Log venue distribution
            venue_counts = {}
            for market in canonical_markets:
                try:
                    venue_name = market.rules_text.venue.name if market.rules_text and market.rules_text.venue else "unknown"
                    venue_counts[venue_name] = venue_counts.get(venue_name, 0) + 1
                except Exception:
                    venue_counts["unknown"] = venue_counts.get("unknown", 0) + 1
            
            self.logger.info(f"Analyzing {len(canonical_markets)} markets for potential pairs using vectorization")
            self.logger.info(f"Venue distribution: {venue_counts}")
            
            # Find similar market pairs using vectorization
            similar_pairs = await market_vectorizer.find_all_similar_pairs(
                canonical_markets,
                threshold=similarity_threshold,
                max_pairs_per_market=5  # Increased to find more pairs
            )
            
            if not similar_pairs:
                self.logger.info("No similar market pairs found above threshold")
                return []
            
            self.logger.info(f"Found {len(similar_pairs)} similar market pairs, analyzing with LLM")
            
            # Analyze similar pairs with LLM for equivalence
            created_pairs = []
            for vector1, vector2, similarity in similar_pairs:
                try:
                    # Get the actual CanonicalMarket objects
                    market1 = next(m for m in canonical_markets if m.id == vector1.market_id)
                    market2 = next(m for m in canonical_markets if m.id == vector2.market_id)
                    
                    # Skip if already paired
                    existing_pair = db.query(Pairs).filter(
                        ((Pairs.market_a_id == market1.id) & (Pairs.market_b_id == market2.id)) |
                        ((Pairs.market_a_id == market2.id) & (Pairs.market_b_id == market1.id))
                    ).first()
                    
                    if existing_pair:
                        continue
                    
                    # Analyze with LLM
                    pair_data = await equivalence_llm_service.analyze_equivalence(market1, market2)
                    
                    if pair_data and pair_data.get("equivalence_score", 0) > 0.5:
                        pair = Pairs(**pair_data)
                        db.add(pair)
                        created_pairs.append(pair)
                        self.logger.info(f"Created pair: {market1.canonical_id} <-> {market2.canonical_id} (score: {pair_data.get('equivalence_score', 0):.2f})")
                    
                except Exception as e:
                    self.logger.error(f"Failed to analyze pair {vector1.canonical_id} <-> {vector2.canonical_id}: {e}")
                    continue
            
            db.commit()
            self.logger.info(f"Created {len(created_pairs)} market pairs using vectorization + LLM")
            return created_pairs
            
        except Exception as e:
            self.logger.error(f"Error in find_and_create_pairs: {e}")
            db.rollback()
            return []
        finally:
            db.close()
    
    async def normalize_single_market(self, rules_text_id: str) -> Optional[CanonicalMarket]:
        """Normalize a single market by its rules_text_id."""
        db = next(get_db())
        
        rules_text = db.query(RulesText).filter(RulesText.id == rules_text_id).first()
        db.close()
        
        if not rules_text:
            self.logger.error(f"Rules text not found: {rules_text_id}")
            return None
        
        return await canonizer_service.normalize_market(rules_text)
    
    async def find_pairs_for_market(self, canonical_market_id: str) -> List[Pairs]:
        """Find all pairs for a specific canonical market."""
        db = next(get_db())
        
        market = db.query(CanonicalMarket).filter(CanonicalMarket.id == canonical_market_id).first()
        if not market:
            self.logger.error(f"Canonical market not found: {canonical_market_id}")
            db.close()
            return []
        
        # Get all other markets
        other_markets = db.query(CanonicalMarket).filter(
            CanonicalMarket.id != canonical_market_id
        ).all()
        
        db.close()
        
        pairs = []
        for other_market in other_markets:
            # Skip if markets are from the same venue
            if market.rules_text.venue_id == other_market.rules_text.venue_id:
                continue
            
            # Skip if markets are in different categories
            if market.category != other_market.category:
                continue
            
            pair = await equivalence_llm_service.create_pair(market, other_market)
            if pair:
                pairs.append(pair)
        
        return pairs
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get the current status of the pipeline."""
        db = next(get_db())
        
        # Count total rules_text records
        total_rules_text = db.query(RulesText).count()
        
        # Count total canonical_market records
        total_canonical_markets = db.query(CanonicalMarket).count()
        
        # Count total pairs
        total_pairs = db.query(Pairs).count()
        
        # Count active pairs
        active_pairs = db.query(Pairs).filter(Pairs.status == "active").count()
        
        # Count pairs by equivalence score ranges
        high_confidence_pairs = db.query(Pairs).filter(Pairs.equivalence_score >= 0.9).count()
        medium_confidence_pairs = db.query(Pairs).filter(
            Pairs.equivalence_score >= 0.7,
            Pairs.equivalence_score < 0.9
        ).count()
        low_confidence_pairs = db.query(Pairs).filter(Pairs.equivalence_score < 0.7).count()
        
        db.close()
        
        # Get normalization progress from canonizer
        normalization_progress = await canonizer_service.get_normalization_progress()
        
        return {
            "total_rules_text": total_rules_text,
            "total_canonical_markets": total_canonical_markets,
            "normalization_coverage": total_canonical_markets / total_rules_text if total_rules_text > 0 else 0,
            "total_pairs": total_pairs,
            "active_pairs": active_pairs,
            "high_confidence_pairs": high_confidence_pairs,
            "medium_confidence_pairs": medium_confidence_pairs,
            "low_confidence_pairs": low_confidence_pairs,
            "normalization_progress": normalization_progress
        }
    
    async def cleanup_inactive_pairs(self, days_threshold: int = 30) -> int:
        """Clean up pairs that haven't been updated in a while."""
        db = next(get_db())
        
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        # Find pairs that haven't been updated recently
        inactive_pairs = db.query(Pairs).filter(
            Pairs.updated_at < cutoff_date,
            Pairs.status == "active"
        ).all()
        
        # Mark as inactive
        for pair in inactive_pairs:
            pair.status = "inactive"
        
        db.commit()
        db.close()
        
        self.logger.info(f"Marked {len(inactive_pairs)} pairs as inactive")
        return len(inactive_pairs)


# Global instance
normalization_pipeline = NormalizationPipeline()
