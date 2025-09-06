"""
Market Vectorization Service

This service handles vectorizing market data for efficient similarity search,
reducing the need for expensive LLM comparisons.
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
from pathlib import Path
import re

from app.database import get_db
from app.models.canonical_market import CanonicalMarket
from app.models.rules_text import RulesText


@dataclass
class MarketVector:
    """Represents a vectorized market for similarity search."""
    market_id: str
    canonical_id: str
    question_text: str
    venue_name: str
    vector: np.ndarray
    metadata: Dict


class MarketVectorizer:
    """Service for vectorizing markets and finding similar ones."""
    
    def __init__(self, max_features: int = 1000):
        """
        Initialize the vectorizer with TF-IDF vectorization.
        
        Args:
            max_features: Maximum number of features for TF-IDF
        """
        self.logger = logging.getLogger(__name__)
        self.max_features = max_features
        self.vectorizer = None
        self.vectors_cache = {}
        self.cache_file = Path("data/market_vectors.pkl")
        
    def _load_vectorizer(self):
        """Initialize the TF-IDF vectorizer."""
        if self.vectorizer is None:
            self.logger.info("Initializing TF-IDF vectorizer")
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                stop_words='english',
                ngram_range=(1, 2),  # Use unigrams and bigrams
                min_df=1,  # Minimum document frequency
                max_df=1.0,  # Maximum document frequency (allow all terms)
                lowercase=True,
                strip_accents='unicode'
            )
            self.logger.info("TF-IDF vectorizer initialized")
    
    async def _load_vectors_cache(self):
        """Load cached vectors from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.vectors_cache = pickle.load(f)
                self.logger.info(f"Loaded {len(self.vectors_cache)} cached vectors")
            except Exception as e:
                self.logger.warning(f"Failed to load vectors cache: {e}")
                self.vectors_cache = {}
    
    async def _save_vectors_cache(self):
        """Save vectors cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.vectors_cache, f)
            self.logger.info(f"Saved {len(self.vectors_cache)} vectors to cache")
        except Exception as e:
            self.logger.error(f"Failed to save vectors cache: {e}")
    
    def _create_market_text(self, market: CanonicalMarket) -> str:
        """Create a text representation of a market for vectorization."""
        # Combine question text, category, and tags for better similarity matching
        text_parts = [market.question_text]
        
        if market.category:
            text_parts.append(market.category)
        
        if market.tags:
            if isinstance(market.tags, list):
                text_parts.extend(market.tags)
            else:
                text_parts.append(str(market.tags))
        
        # Clean and normalize the text
        combined_text = " ".join(text_parts)
        # Remove special characters and normalize whitespace
        cleaned_text = re.sub(r'[^\w\s]', ' ', combined_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    async def vectorize_market(self, market: CanonicalMarket) -> MarketVector:
        """Vectorize a single market."""
        self._load_vectorizer()
        
        # Create text representation
        market_text = self._create_market_text(market)
        
        # Generate TF-IDF vector
        vector = self.vectorizer.fit_transform([market_text]).toarray()[0]
        
        # Get venue name safely
        venue_name = "unknown"
        try:
            if market.rules_text and market.rules_text.venue:
                venue_name = market.rules_text.venue.name
        except Exception:
            venue_name = "unknown"
        
        return MarketVector(
            market_id=market.id,
            canonical_id=market.canonical_id,
            question_text=market.question_text,
            venue_name=venue_name,
            vector=vector,
            metadata={
                "category": market.category,
                "tags": market.tags,
                "text": market_text
            }
        )
    
    async def vectorize_markets_batch(self, markets: List[CanonicalMarket]) -> List[MarketVector]:
        """Vectorize multiple markets efficiently."""
        self._load_vectorizer()
        
        # Prepare texts for batch encoding
        texts = []
        market_metadata = []
        
        for market in markets:
            text = self._create_market_text(market)
            texts.append(text)
            market_metadata.append({
                "market": market,
                "text": text
            })
        
        # Batch encode for efficiency using TF-IDF
        vectors = self.vectorizer.fit_transform(texts).toarray()
        
        # Create MarketVector objects
        result = []
        for i, (vector, metadata) in enumerate(zip(vectors, market_metadata)):
            market = metadata["market"]
            
            # Get venue name safely
            venue_name = "unknown"
            try:
                if market.rules_text and market.rules_text.venue:
                    venue_name = market.rules_text.venue.name
            except Exception:
                venue_name = "unknown"
            
            result.append(MarketVector(
                market_id=market.id,
                canonical_id=market.canonical_id,
                question_text=market.question_text,
                venue_name=venue_name,
                vector=vector,
                metadata={
                    "category": market.category,
                    "tags": market.tags,
                    "text": metadata["text"]
                }
            ))
        
        return result
    
    async def find_similar_markets(
        self, 
        target_market: MarketVector, 
        all_vectors: List[MarketVector],
        threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Tuple[MarketVector, float]]:
        """
        Find markets similar to the target market.
        
        Args:
            target_market: The market to find similarities for
            all_vectors: List of all market vectors to search
            threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results to return
            
        Returns:
            List of (MarketVector, similarity_score) tuples
        """
        if not all_vectors:
            return []
        
        # Calculate similarities
        target_vector = target_market.vector.reshape(1, -1)
        other_vectors = np.array([mv.vector for mv in all_vectors])
        
        similarities = cosine_similarity(target_vector, other_vectors)[0]
        
        # Find similar markets above threshold
        similar_markets = []
        for i, similarity in enumerate(similarities):
            if similarity >= threshold and all_vectors[i].market_id != target_market.market_id:
                similar_markets.append((all_vectors[i], similarity))
        
        # Sort by similarity and limit results
        similar_markets.sort(key=lambda x: x[1], reverse=True)
        return similar_markets[:max_results]
    
    async def find_all_similar_pairs(
        self, 
        markets: List[CanonicalMarket],
        threshold: float = 0.7,
        max_pairs_per_market: int = 5
    ) -> List[Tuple[MarketVector, MarketVector, float]]:
        """
        Find all similar market pairs efficiently, only comparing across different venues.
        
        Args:
            markets: List of markets to analyze
            threshold: Minimum similarity score
            max_pairs_per_market: Maximum pairs to return per market
            
        Returns:
            List of (market1, market2, similarity_score) tuples
        """
        if len(markets) < 2:
            return []
        
        # Vectorize all markets
        self.logger.info(f"Vectorizing {len(markets)} markets")
        vectors = await self.vectorize_markets_batch(markets)
        
        # Find similar pairs
        similar_pairs = []
        processed_pairs = set()  # Avoid duplicate pairs
        
        for i, target_vector in enumerate(vectors):
            # Find similar markets for this target
            similar_markets = await self.find_similar_markets(
                target_vector, 
                vectors[i+1:],  # Only check markets we haven't processed yet
                threshold=threshold,
                max_results=max_pairs_per_market
            )
            
            for similar_vector, similarity in similar_markets:
                # Skip if markets are from the same venue (no arbitrage opportunity)
                if target_vector.venue_name == similar_vector.venue_name:
                    continue
                
                # Create a unique pair identifier
                pair_id = tuple(sorted([target_vector.market_id, similar_vector.market_id]))
                if pair_id not in processed_pairs:
                    similar_pairs.append((target_vector, similar_vector, similarity))
                    processed_pairs.add(pair_id)
        
        self.logger.info(f"Found {len(similar_pairs)} cross-venue similar market pairs above threshold {threshold}")
        return similar_pairs
    
    async def find_similar_pairs_for_new_markets(
        self, 
        new_markets: List[CanonicalMarket],
        all_markets: List[CanonicalMarket],
        threshold: float = 0.7,
        max_pairs_per_market: int = 5
    ) -> List[Tuple[MarketVector, MarketVector, float]]:
        """
        Find similar pairs between new markets and all existing markets.
        
        Args:
            new_markets: List of newly added markets
            all_markets: List of all markets (including new ones)
            threshold: Minimum similarity score
            max_pairs_per_market: Maximum pairs to return per new market
            
        Returns:
            List of (new_market_vector, existing_market_vector, similarity_score) tuples
        """
        if not new_markets or len(all_markets) < 2:
            return []
        
        # Vectorize all markets
        self.logger.info(f"Vectorizing {len(all_markets)} markets for new market pair finding")
        all_vectors = await self.vectorize_markets_batch(all_markets)
        
        # Create lookup for new market vectors
        new_market_ids = {m.id for m in new_markets}
        new_vectors = [v for v in all_vectors if v.market_id in new_market_ids]
        existing_vectors = [v for v in all_vectors if v.market_id not in new_market_ids]
        
        if not new_vectors or not existing_vectors:
            return []
        
        # Find similar pairs
        similar_pairs = []
        processed_pairs = set()  # Avoid duplicate pairs
        
        for new_vector in new_vectors:
            # Find similar existing markets for this new market
            similar_markets = await self.find_similar_markets(
                new_vector, 
                existing_vectors,
                threshold=threshold,
                max_results=max_pairs_per_market
            )
            
            for similar_vector, similarity in similar_markets:
                # Skip if markets are from the same venue (no arbitrage opportunity)
                if new_vector.venue_name == similar_vector.venue_name:
                    continue
                
                # Create a unique pair identifier
                pair_id = tuple(sorted([new_vector.market_id, similar_vector.market_id]))
                if pair_id not in processed_pairs:
                    similar_pairs.append((new_vector, similar_vector, similarity))
                    processed_pairs.add(pair_id)
        
        self.logger.info(f"Found {len(similar_pairs)} similar pairs between new and existing markets above threshold {threshold}")
        return similar_pairs
    
    async def get_all_canonical_markets(self) -> List[CanonicalMarket]:
        """Get all canonical markets from the database."""
        db = next(get_db())
        try:
            # Eager load relationships to avoid lazy loading issues
            from sqlalchemy.orm import joinedload
            markets = db.query(CanonicalMarket).options(
                joinedload(CanonicalMarket.rules_text).joinedload(RulesText.venue)
            ).all()
            
            # Access the relationships while the session is still open
            for market in markets:
                if market.rules_text and market.rules_text.venue:
                    # This will populate the relationship
                    _ = market.rules_text.venue.name
            
            return markets
        finally:
            db.close()
    
    async def update_vectors_cache(self, markets: List[CanonicalMarket]):
        """Update the vectors cache with new markets."""
        await self._load_vectors_cache()
        
        # Vectorize new markets
        new_vectors = await self.vectorize_markets_batch(markets)
        
        # Update cache
        for vector in new_vectors:
            self.vectors_cache[vector.market_id] = vector
        
        # Save to disk
        await self._save_vectors_cache()
    
    async def get_cached_vector(self, market_id: str) -> Optional[MarketVector]:
        """Get a cached vector for a market."""
        await self._load_vectors_cache()
        return self.vectors_cache.get(market_id)


# Global instance
market_vectorizer = MarketVectorizer()
