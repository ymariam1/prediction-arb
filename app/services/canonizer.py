"""
Canonizer Service

This service parses raw market rules text into a canonical, normalized schema.
It uses LLM services to extract structured information from unstructured text.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
import hashlib
import pickle
from pathlib import Path

from app.config import settings
from app.models.canonical_market import CanonicalMarket
from app.models.rules_text import RulesText
from app.database import get_db


class CanonizerService:
    """Service for normalizing market rules into canonical format."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_provider = settings.llm_provider
        self.llm_model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        # Caching setup
        self.cache_dir = Path("data/normalization_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "normalized_markets.pkl"
        self.normalization_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load normalization cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.normalization_cache = pickle.load(f)
                self.logger.info(f"Loaded {len(self.normalization_cache)} cached normalizations")
            except Exception as e:
                self.logger.warning(f"Failed to load normalization cache: {e}")
                self.normalization_cache = {}
    
    def _save_cache(self):
        """Save normalization cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.normalization_cache, f)
            self.logger.info(f"Saved {len(self.normalization_cache)} normalizations to cache")
        except Exception as e:
            self.logger.error(f"Failed to save normalization cache: {e}")
    
    def _get_cache_key(self, rules_text: RulesText) -> str:
        """Generate a cache key for a rules text."""
        # Create a hash based on the rules text content and venue
        content = f"{rules_text.rules_text}_{rules_text.venue.name}_{rules_text.market_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_normalization(self, rules_text: RulesText) -> Optional[Dict[str, Any]]:
        """Get cached normalization data for a rules text."""
        cache_key = self._get_cache_key(rules_text)
        return self.normalization_cache.get(cache_key)
    
    def _cache_normalization(self, rules_text: RulesText, normalized_data: Dict[str, Any]):
        """Cache normalization data for a rules text."""
        cache_key = self._get_cache_key(rules_text)
        self.normalization_cache[cache_key] = normalized_data
        self._save_cache()
        
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call the configured LLM service."""
        try:
            if self.llm_provider == "openai":
                return await self._call_openai(prompt, system_prompt)
            elif self.llm_provider == "anthropic":
                return await self._call_anthropic(prompt, system_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise
    
    async def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
        """Call OpenAI API."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.llm_model,
            "messages": messages
        }
        
        # Handle different parameter names for different models
        if self.llm_model.startswith("o3"):
            data["max_completion_tokens"] = self.max_tokens
            # O3 models only support default temperature (1)
        else:
            data["max_tokens"] = self.max_tokens
            data["temperature"] = self.temperature
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    async def _call_anthropic(self, prompt: str, system_prompt: str = None) -> str:
        """Call Anthropic API."""
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.llm_model,
            "max_completion_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result["content"][0]["text"]
    
    def _generate_canonical_id(self, rules_text: RulesText, venue_name: str) -> str:
        """Generate a canonical ID for the market."""
        # Use venue name, market ID, and a hash of the rules text
        import hashlib
        content_hash = hashlib.md5(rules_text.rules_text.encode()).hexdigest()[:8]
        return f"{venue_name}_{rules_text.market_id}_{content_hash}"
    
    async def normalize_market(self, rules_text: RulesText) -> Optional[CanonicalMarket]:
        """Normalize a single market's rules text into canonical format."""
        try:
            # Get venue name while session is open
            db = next(get_db())
            venue_name = rules_text.venue.name
            self.logger.info(f"Normalizing market {rules_text.market_id} from {venue_name}")
            
            # Check if already normalized in database
            existing = db.query(CanonicalMarket).filter(
                CanonicalMarket.rules_text_id == rules_text.id
            ).first()
            if existing:
                self.logger.info(f"Market {rules_text.market_id} already normalized")
                db.close()
                return existing
            
            # Check cache first
            cached_data = self._get_cached_normalization(rules_text)
            if cached_data:
                self.logger.info(f"Using cached normalization for market {rules_text.market_id}")
                # Create canonical market from cached data
                canonical_id = self._generate_canonical_id(rules_text, venue_name)
                canonical_market = CanonicalMarket(
                    rules_text_id=rules_text.id,
                    canonical_id=canonical_id,
                    question_text=cached_data.get("question_text", ""),
                    outcome_options=cached_data.get("outcome_options", []),
                    resolution_criteria=cached_data.get("resolution_criteria", {}),
                    category=cached_data.get("category", "uncategorized"),
                    tags=cached_data.get("tags", [])
                )
                
                # Save to database
                db.add(canonical_market)
                db.commit()
                db.refresh(canonical_market)
                db.close()
                
                self.logger.info(f"Successfully normalized market {rules_text.market_id} from cache")
                return canonical_market
            
            # Create the normalization prompt - optimized for speed
            system_prompt = """You are an expert at analyzing prediction market rules. Extract key information quickly and accurately.

            Return ONLY a JSON object with this exact structure:
            {
                "question_text": "Clear, normalized question",
                "outcome_options": ["Option 1", "Option 2"],
                "resolution_criteria": {
                    "description": "How resolved",
                    "deadline": "When resolved", 
                    "authority": "Who decides"
                },
                "category": "politics|sports|economics|technology|other",
                "tags": ["tag1", "tag2"]
            }
            
            Be concise and accurate. Focus on the essential information."""
            
            prompt = f"""Extract structured information from this prediction market:

Market: {rules_text.market_id} ({rules_text.venue.name})
Resolution: {rules_text.resolution_date}

{rules_text.rules_text}

Return JSON only."""
            
            # Call LLM
            response = await self._call_llm(prompt, system_prompt)
            
            # Parse the response
            try:
                normalized_data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    normalized_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse LLM response as JSON")
            
            # Cache the normalization data
            self._cache_normalization(rules_text, normalized_data)
            
            # Create canonical market record
            canonical_id = self._generate_canonical_id(rules_text, venue_name)
            
            canonical_market = CanonicalMarket(
                rules_text_id=rules_text.id,
                canonical_id=canonical_id,
                question_text=normalized_data.get("question_text", ""),
                outcome_options=normalized_data.get("outcome_options", []),
                resolution_criteria=normalized_data.get("resolution_criteria", {}),
                category=normalized_data.get("category", "uncategorized"),
                tags=normalized_data.get("tags", [])
            )
            
            # Save to database
            db.add(canonical_market)
            db.commit()
            db.refresh(canonical_market)
            db.close()
            
            self.logger.info(f"Successfully normalized market {rules_text.market_id}")
            return canonical_market
            
        except Exception as e:
            self.logger.error(f"Failed to normalize market {rules_text.market_id}: {e}")
            if 'db' in locals():
                db.close()
            return None
    
    async def normalize_markets_batch(self, rules_texts: List[RulesText]) -> List[CanonicalMarket]:
        """Normalize multiple markets in parallel with optimized batching."""
        self.logger.info(f"Starting batch normalization of {len(rules_texts)} markets")
        
        # Optimized batch size based on LLM provider
        if self.llm_provider == "openai":
            batch_size = 5  # OpenAI can handle more concurrent requests
            delay_between_batches = 1.0
        else:
            batch_size = 3  # Anthropic is more conservative
            delay_between_batches = 1.5
        
        results = []
        total_batches = (len(rules_texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(rules_texts), batch_size):
            batch = rules_texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} markets)")
            
            # Process batch in parallel with semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(batch_size)
            
            async def normalize_with_semaphore(rules_text):
                async with semaphore:
                    return await self.normalize_market(rules_text)
            
            tasks = [normalize_with_semaphore(rules_text) for rules_text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            batch_success_count = 0
            for result in batch_results:
                if isinstance(result, CanonicalMarket):
                    results.append(result)
                    batch_success_count += 1
                elif isinstance(result, Exception):
                    self.logger.error(f"Batch processing error: {result}")
            
            self.logger.info(f"Batch {batch_num} completed: {batch_success_count}/{len(batch)} successful")
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(rules_texts):
                await asyncio.sleep(delay_between_batches)
        
        self.logger.info(f"Batch normalization completed. {len(results)}/{len(rules_texts)} markets normalized successfully")
        return results
    
    async def normalize_all_pending_markets(self) -> List[CanonicalMarket]:
        """Normalize all markets that haven't been processed yet."""
        db = next(get_db())
        
        # Find all rules_text records that don't have canonical_market records
        # Eager load venue to avoid lazy loading issues
        from sqlalchemy.orm import joinedload
        pending_rules = db.query(RulesText).options(
            joinedload(RulesText.venue)
        ).outerjoin(
            CanonicalMarket, RulesText.id == CanonicalMarket.rules_text_id
        ).filter(CanonicalMarket.id.is_(None)).all()
        
        db.close()
        
        if not pending_rules:
            self.logger.info("No pending markets to normalize")
            return []
        
        self.logger.info(f"Found {len(pending_rules)} pending markets to normalize")
        return await self.normalize_markets_batch(pending_rules)
    
    async def normalize_new_markets_only(self, limit: int = None) -> List[CanonicalMarket]:
        """Normalize only the most recently added markets (for incremental processing)."""
        db = next(get_db())
        
        # Find the most recent rules_text records that haven't been processed
        from sqlalchemy.orm import joinedload
        query = db.query(RulesText).options(
            joinedload(RulesText.venue)
        ).outerjoin(
            CanonicalMarket, RulesText.id == CanonicalMarket.rules_text_id
        ).filter(CanonicalMarket.id.is_(None)).order_by(RulesText.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        pending_rules = query.all()
        db.close()
        
        if not pending_rules:
            self.logger.info("No new markets to normalize")
            return []
        
        self.logger.info(f"Found {len(pending_rules)} new markets to normalize")
        return await self.normalize_markets_batch(pending_rules)
    
    async def get_normalization_progress(self) -> Dict[str, Any]:
        """Get progress information about normalization."""
        db = next(get_db())
        
        # Count total rules_text records
        total_rules = db.query(RulesText).count()
        
        # Count normalized markets
        normalized_count = db.query(CanonicalMarket).count()
        
        # Count pending markets
        pending_count = db.query(RulesText).outerjoin(
            CanonicalMarket, RulesText.id == CanonicalMarket.rules_text_id
        ).filter(CanonicalMarket.id.is_(None)).count()
        
        # Get recent activity
        from datetime import datetime, timedelta
        recent_threshold = datetime.now() - timedelta(days=7)
        recent_rules = db.query(RulesText).filter(
            RulesText.created_at >= recent_threshold
        ).count()
        
        db.close()
        
        return {
            "total_rules_text": total_rules,
            "normalized_markets": normalized_count,
            "pending_markets": pending_count,
            "normalization_percentage": (normalized_count / total_rules * 100) if total_rules > 0 else 0,
            "recent_rules_7_days": recent_rules
        }


# Global instance
canonizer_service = CanonizerService()
