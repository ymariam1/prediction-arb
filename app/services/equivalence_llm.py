"""
Equivalence LLM Service

This service uses LLM to determine if two canonical markets are equivalent
and can be used for arbitrage opportunities.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
import aiohttp

from app.config import settings
from app.models.canonical_market import CanonicalMarket
from app.models.pairs import Pairs
from app.database import get_db


class EquivalenceLLMService:
    """Service for determining market equivalence using LLM."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_provider = settings.llm_provider
        self.llm_model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
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
            "max_tokens": self.max_tokens,
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
    
    async def analyze_equivalence(self, market_a: CanonicalMarket, market_b: CanonicalMarket) -> Dict[str, Any]:
        """Analyze if two markets are equivalent for arbitrage purposes."""
        try:
            self.logger.info(f"Analyzing equivalence between {market_a.canonical_id} and {market_b.canonical_id}")
            
            system_prompt = """You are an expert at analyzing prediction markets for arbitrage opportunities. 
            Your task is to determine if two markets are equivalent and can be used for arbitrage.
            
            IMPORTANT: Use chain-of-thought reasoning. Think step by step:
            1. First, analyze what each market is asking about
            2. Compare the core events/outcomes being predicted
            3. Check if resolution criteria are compatible
            4. Verify timing constraints for arbitrage
            5. Assess outcome alignment and mutual exclusivity
            6. Identify any potential conflicts or edge cases
            7. Synthesize your findings into a final score
            
            Two markets are equivalent if:
            1. They ask the same question about the same event
            2. They have the same resolution criteria
            3. They resolve at the same time or close enough for arbitrage
            4. The outcomes are mutually exclusive and collectively exhaustive
            
            Return a JSON object with the following structure:
            {
                "equivalence_score": 0.95,  // Score from 0.0 to 1.0
                "hard_ok": true,            // Whether hard constraints are satisfied
                "confidence": 0.9,          // Confidence in the analysis (0.0 to 1.0)
                "conflict_list": [          // List of identified conflicts
                    "Resolution dates differ by more than 1 day",
                    "Outcome options don't match exactly"
                ],
                "reasoning": "Step-by-step analysis: 1) Market A asks about X, Market B asks about Y... 2) Core events comparison... 3) Resolution criteria analysis... 4) Timing assessment... 5) Outcome alignment... 6) Final synthesis..."
            }
            
            Be thorough, conservative, and show your reasoning process."""
            
            prompt = f"""Please analyze if these two prediction markets are equivalent for arbitrage purposes:

MARKET A:
- ID: {market_a.canonical_id}
- Question: {market_a.question_text}
- Outcomes: {json.dumps(market_a.outcome_options)}
- Resolution Criteria: {json.dumps(market_a.resolution_criteria)}
- Category: {market_a.category}
- Tags: {json.dumps(market_a.tags)}

MARKET B:
- ID: {market_b.canonical_id}
- Question: {market_b.question_text}
- Outcomes: {json.dumps(market_b.outcome_options)}
- Resolution Criteria: {json.dumps(market_b.resolution_criteria)}
- Category: {market_b.category}
- Tags: {json.dumps(market_b.tags)}

Please provide your analysis as a JSON object."""
            
            # Call LLM
            response = await self._call_llm(prompt, system_prompt)
            
            # Parse the response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse LLM response as JSON")
            
            # Validate the response structure
            required_fields = ["equivalence_score", "hard_ok", "confidence", "conflict_list", "reasoning"]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure scores are within valid ranges
            analysis["equivalence_score"] = max(0.0, min(1.0, float(analysis["equivalence_score"])))
            analysis["confidence"] = max(0.0, min(1.0, float(analysis["confidence"])))
            analysis["hard_ok"] = bool(analysis["hard_ok"])
            
            self.logger.info(f"Equivalence analysis completed: score={analysis['equivalence_score']}, hard_ok={analysis['hard_ok']}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze equivalence between {market_a.canonical_id} and {market_b.canonical_id}: {e}")
            # Return a default analysis indicating no equivalence
            return {
                "equivalence_score": 0.0,
                "hard_ok": False,
                "confidence": 0.0,
                "conflict_list": [f"Analysis failed: {str(e)}"],
                "reasoning": f"Failed to analyze equivalence due to error: {str(e)}"
            }
    
    async def create_pair(self, market_a: CanonicalMarket, market_b: CanonicalMarket) -> Optional[Pairs]:
        """Create a pair record if markets are equivalent."""
        try:
            # Check if pair already exists
            db = next(get_db())
            existing_pair = db.query(Pairs).filter(
                ((Pairs.market_a_id == market_a.id) & (Pairs.market_b_id == market_b.id)) |
                ((Pairs.market_a_id == market_b.id) & (Pairs.market_b_id == market_a.id))
            ).first()
            
            if existing_pair:
                self.logger.info(f"Pair already exists between {market_a.canonical_id} and {market_b.canonical_id}")
                db.close()
                return existing_pair
            
            # Analyze equivalence
            analysis = await self.analyze_equivalence(market_a, market_b)
            
            # Only create pair if equivalence score is above threshold
            min_equivalence_score = 0.7  # Configurable threshold
            if analysis["equivalence_score"] < min_equivalence_score:
                self.logger.info(f"Equivalence score too low ({analysis['equivalence_score']}) for pair creation")
                db.close()
                return None
            
            # Create pair record
            pair = Pairs(
                market_a_id=market_a.id,
                market_b_id=market_b.id,
                equivalence_score=analysis["equivalence_score"],
                conflict_list=analysis["conflict_list"],
                hard_ok=analysis["hard_ok"],
                confidence=analysis["confidence"],
                status="active"
            )
            
            db.add(pair)
            db.commit()
            db.refresh(pair)
            db.close()
            
            self.logger.info(f"Created pair between {market_a.canonical_id} and {market_b.canonical_id} with score {analysis['equivalence_score']}")
            return pair
            
        except Exception as e:
            self.logger.error(f"Failed to create pair between {market_a.canonical_id} and {market_b.canonical_id}: {e}")
            if 'db' in locals():
                db.close()
            return None
    
    async def find_potential_pairs(self, markets: List[CanonicalMarket]) -> List[Pairs]:
        """Find potential pairs among a list of markets."""
        self.logger.info(f"Finding potential pairs among {len(markets)} markets")
        
        pairs = []
        total_combinations = len(markets) * (len(markets) - 1) // 2
        
        for i, market_a in enumerate(markets):
            for j, market_b in enumerate(markets[i+1:], i+1):
                self.logger.info(f"Analyzing pair {i*len(markets) + j - i*(i+1)//2 + 1}/{total_combinations}")
                
                # Skip if markets are from the same venue (no arbitrage opportunity)
                if market_a.rules_text.venue_id == market_b.rules_text.venue_id:
                    continue
                
                # Skip if markets are in different categories (likely not equivalent)
                if market_a.category != market_b.category:
                    continue
                
                pair = await self.create_pair(market_a, market_b)
                if pair:
                    pairs.append(pair)
                
                # Add delay to respect rate limits
                await asyncio.sleep(0.5)
        
        self.logger.info(f"Found {len(pairs)} potential pairs")
        return pairs
    
    async def find_all_potential_pairs(self) -> List[Pairs]:
        """Find all potential pairs in the database."""
        db = next(get_db())
        
        # Get all canonical markets
        markets = db.query(CanonicalMarket).all()
        db.close()
        
        if len(markets) < 2:
            self.logger.info("Not enough markets to find pairs")
            return []
        
        return await self.find_potential_pairs(markets)


# Global instance
equivalence_llm_service = EquivalenceLLMService()
