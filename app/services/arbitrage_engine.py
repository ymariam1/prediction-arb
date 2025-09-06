"""
Arbitrage Detection Engine

This service analyzes matched market pairs and live order books to identify
arbitrage opportunities and calculate executable sizes.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from app.config import settings
from app.database import get_db
from app.models.pairs import Pairs
from app.models.canonical_market import CanonicalMarket
from app.models.book_levels import BookLevels
from app.models.arbitrage_signals import ArbitrageSignals
from app.models.venue import Venue


@dataclass
class OrderBookSnapshot:
    """Snapshot of order book data for a market."""
    market_id: str
    venue_name: str
    best_bid: Optional[float]
    best_ask: Optional[float]
    bid_size: Optional[float]
    ask_size: Optional[float]
    timestamp: datetime
    is_stale: bool = False


@dataclass
class ArbitrageCalculation:
    """Result of arbitrage calculation."""
    is_arbitrage: bool
    total_cost: float
    edge_buffer: float
    executable_size: float
    strategy: str
    direction_a: str
    direction_b: str
    market_a_snapshot: OrderBookSnapshot
    market_b_snapshot: OrderBookSnapshot
    fees_a: float
    fees_b: float
    slippage_buffer: float
    confidence: float
    metadata: Dict[str, Any]


class ArbitrageEngine:
    """
    Core arbitrage detection engine that analyzes market pairs and order books
    to identify profitable arbitrage opportunities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.min_edge_buffer = 0.02  # 2% minimum edge buffer
        self.max_slippage = 0.01  # 1% maximum slippage buffer
        self.book_staleness_threshold = 30  # 30 seconds
        self.min_executable_size = 10.0  # Minimum $10 executable size
        
        # Venue-specific fee structures (in basis points)
        self.venue_fees = {
            "kalshi": 0.001,  # 0.1%
            "polymarket": 0.002,  # 0.2%
        }
        
    async def analyze_all_pairs(self) -> List[ArbitrageSignals]:
        """Analyze all active market pairs for arbitrage opportunities."""
        db = next(get_db())
        
        try:
            # Get all active pairs
            active_pairs = db.query(Pairs).filter(
                Pairs.status == "active",
                Pairs.hard_ok == True,
                Pairs.equivalence_score >= 0.7  # Only high-confidence pairs
            ).all()
            
            if not active_pairs:
                self.logger.info("No active pairs found for arbitrage analysis")
                return []
            
            self.logger.info(f"Analyzing {len(active_pairs)} active pairs for arbitrage opportunities")
            
            signals = []
            for pair in active_pairs:
                try:
                    signal = await self.analyze_pair(pair, db_session=db)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    self.logger.error(f"Failed to analyze pair {pair.id}: {e}")
                    continue
            
            # Save signals to database
            if signals:
                db.add_all(signals)
                db.commit()
                self.logger.info(f"Created {len(signals)} arbitrage signals")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in analyze_all_pairs: {e}")
            db.rollback()
            return []
        finally:
            db.close()
    
    async def analyze_pair(self, pair: Pairs, db_session=None) -> Optional[ArbitrageSignals]:
        """Analyze a single market pair for arbitrage opportunities."""
        if db_session is None:
            db = next(get_db())
            should_close = True
        else:
            db = db_session
            should_close = False
        
        try:
            # Get market details with eager loading
            market_a = db.query(CanonicalMarket).filter(
                CanonicalMarket.id == pair.market_a_id
            ).first()
            market_b = db.query(CanonicalMarket).filter(
                CanonicalMarket.id == pair.market_b_id
            ).first()
            
            if not market_a or not market_b:
                self.logger.warning(f"Missing market data for pair {pair.id}")
                return None
            
            # Get order book snapshots
            snapshot_a = await self._get_order_book_snapshot(market_a)
            snapshot_b = await self._get_order_book_snapshot(market_b)
            
            if not snapshot_a or not snapshot_b:
                self.logger.warning(f"Missing order book data for pair {pair.id}")
                return None
            
            # Check for stale data
            if snapshot_a.is_stale or snapshot_b.is_stale:
                self.logger.warning(f"Stale order book data for pair {pair.id}")
                return None
            
            # Calculate arbitrage opportunity
            calculation = await self._calculate_arbitrage(
                market_a, market_b, snapshot_a, snapshot_b
            )
            
            if not calculation:
                return None
            
            # Create arbitrage signal
            signal = ArbitrageSignals(
                pair_id=pair.id,
                market_a_id=market_a.id,
                market_b_id=market_b.id,
                total_cost=calculation.total_cost,
                edge_buffer=calculation.edge_buffer,
                is_arbitrage=calculation.is_arbitrage,
                executable_size=calculation.executable_size,
                market_a_best_bid=calculation.market_a_snapshot.best_bid,
                market_a_best_ask=calculation.market_a_snapshot.best_ask,
                market_a_bid_size=calculation.market_a_snapshot.bid_size,
                market_a_ask_size=calculation.market_a_snapshot.ask_size,
                market_a_venue=calculation.market_a_snapshot.venue_name,
                market_b_best_bid=calculation.market_b_snapshot.best_bid,
                market_b_best_ask=calculation.market_b_snapshot.best_ask,
                market_b_bid_size=calculation.market_b_snapshot.bid_size,
                market_b_ask_size=calculation.market_b_snapshot.ask_size,
                market_b_venue=calculation.market_b_snapshot.venue_name,
                market_a_fees=calculation.fees_a,
                market_b_fees=calculation.fees_b,
                slippage_buffer=calculation.slippage_buffer,
                strategy=calculation.strategy,
                direction_a=calculation.direction_a,
                direction_b=calculation.direction_b,
                signal_strength=abs(1.0 - calculation.total_cost),
                confidence=calculation.confidence,
                status="active",
                expires_at=datetime.utcnow() + timedelta(minutes=5),  # 5-minute expiry
                calculation_metadata=calculation.metadata
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error analyzing pair {pair.id}: {e}")
            return None
        finally:
            if should_close:
                db.close()
    
    async def _get_order_book_snapshot(self, market: CanonicalMarket) -> Optional[OrderBookSnapshot]:
        """Get current order book snapshot for a market."""
        db = next(get_db())
        
        try:
            # Get the most recent order book data
            book_data = db.query(BookLevels).filter(
                BookLevels.market_id == market.canonical_id
            ).order_by(BookLevels.created_at.desc()).first()
            
            if not book_data:
                return None
            
            # Check for staleness
            is_stale = (datetime.utcnow() - book_data.created_at).total_seconds() > self.book_staleness_threshold
            
            # Get venue name
            venue_name = "unknown"
            try:
                if market.rules_text and market.rules_text.venue:
                    venue_name = market.rules_text.venue.name
            except Exception:
                pass
            
            # Get all order book levels for this market
            all_levels = db.query(BookLevels).filter(
                BookLevels.market_id == market.canonical_id
            ).all()
            
            # Extract best bid/ask from order book levels
            best_bid = None
            best_ask = None
            bid_size = None
            ask_size = None
            
            # Find best bid (highest price for buy orders)
            bid_levels = [level for level in all_levels if level.side == "bid"]
            if bid_levels:
                best_bid_level = max(bid_levels, key=lambda x: x.price)
                best_bid = best_bid_level.price
                bid_size = best_bid_level.size
            
            # Find best ask (lowest price for sell orders)
            ask_levels = [level for level in all_levels if level.side == "ask"]
            if ask_levels:
                best_ask_level = min(ask_levels, key=lambda x: x.price)
                best_ask = best_ask_level.price
                ask_size = best_ask_level.size
            
            return OrderBookSnapshot(
                market_id=market.canonical_id,
                venue_name=venue_name,
                best_bid=best_bid,
                best_ask=best_ask,
                bid_size=bid_size,
                ask_size=ask_size,
                timestamp=book_data.created_at,
                is_stale=is_stale
            )
            
        except Exception as e:
            self.logger.error(f"Error getting order book snapshot for {market.canonical_id}: {e}")
            return None
        finally:
            db.close()
    
    async def _calculate_arbitrage(
        self, 
        market_a: CanonicalMarket, 
        market_b: CanonicalMarket,
        snapshot_a: OrderBookSnapshot,
        snapshot_b: OrderBookSnapshot
    ) -> Optional[ArbitrageCalculation]:
        """Calculate arbitrage opportunity between two markets."""
        
        # Check if we have valid prices
        if not all([snapshot_a.best_bid, snapshot_a.best_ask, snapshot_b.best_bid, snapshot_b.best_ask]):
            return None
        
        # Calculate straddle cost (buy one market, sell the other)
        # Strategy 1: Buy A, Sell B
        cost_buy_a_sell_b = snapshot_a.best_ask + snapshot_b.best_bid
        
        # Strategy 2: Sell A, Buy B  
        cost_sell_a_buy_b = snapshot_a.best_bid + snapshot_b.best_ask
        
        # Choose the better strategy
        if cost_buy_a_sell_b < cost_sell_a_buy_b:
            total_cost = cost_buy_a_sell_b
            strategy = "buy_a_sell_b"
            direction_a = "buy"
            direction_b = "sell"
            executable_size = min(snapshot_a.ask_size or 0, snapshot_b.bid_size or 0)
        else:
            total_cost = cost_sell_a_buy_b
            strategy = "sell_a_buy_b"
            direction_a = "sell"
            direction_b = "buy"
            executable_size = min(snapshot_a.bid_size or 0, snapshot_b.ask_size or 0)
        
        # Check minimum executable size
        if executable_size < self.min_executable_size:
            return None
        
        # Calculate fees
        fees_a = self._calculate_fees(snapshot_a.venue_name, executable_size)
        fees_b = self._calculate_fees(snapshot_b.venue_name, executable_size)
        
        # Calculate slippage buffer
        slippage_buffer = self._calculate_slippage_buffer(executable_size)
        
        # Total cost including fees and slippage
        total_cost_with_fees = total_cost + fees_a + fees_b + slippage_buffer
        
        # Calculate edge buffer
        edge_buffer = 1.0 - total_cost_with_fees
        
        # Determine if it's an arbitrage opportunity
        is_arbitrage = total_cost_with_fees < (1.0 - self.min_edge_buffer)
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(
            market_a, market_b, snapshot_a, snapshot_b, 
            total_cost_with_fees, executable_size
        )
        
        metadata = {
            "raw_cost": total_cost,
            "fees_breakdown": {
                "market_a": fees_a,
                "market_b": fees_b
            },
            "slippage_buffer": slippage_buffer,
            "strategy_details": {
                "strategy": strategy,
                "direction_a": direction_a,
                "direction_b": direction_b
            },
            "executable_size_details": {
                "market_a_size": snapshot_a.ask_size if direction_a == "buy" else snapshot_a.bid_size,
                "market_b_size": snapshot_b.ask_size if direction_b == "buy" else snapshot_b.bid_size
            }
        }
        
        return ArbitrageCalculation(
            is_arbitrage=is_arbitrage,
            total_cost=total_cost_with_fees,
            edge_buffer=edge_buffer,
            executable_size=executable_size,
            strategy=strategy,
            direction_a=direction_a,
            direction_b=direction_b,
            market_a_snapshot=snapshot_a,
            market_b_snapshot=snapshot_b,
            fees_a=fees_a,
            fees_b=fees_b,
            slippage_buffer=slippage_buffer,
            confidence=confidence,
            metadata=metadata
        )
    
    def _calculate_fees(self, venue_name: str, size: float) -> float:
        """Calculate trading fees for a venue."""
        fee_rate = self.venue_fees.get(venue_name.lower(), 0.002)  # Default 0.2%
        return size * fee_rate
    
    def _calculate_slippage_buffer(self, size: float) -> float:
        """Calculate slippage buffer based on size."""
        # Larger sizes have higher slippage risk
        if size < 100:
            return size * 0.001  # 0.1%
        elif size < 1000:
            return size * 0.002  # 0.2%
        else:
            return size * 0.005  # 0.5%
    
    def _calculate_confidence(
        self, 
        market_a: CanonicalMarket,
        market_b: CanonicalMarket,
        snapshot_a: OrderBookSnapshot,
        snapshot_b: OrderBookSnapshot,
        total_cost: float,
        executable_size: float
    ) -> float:
        """Calculate confidence in the arbitrage opportunity."""
        confidence = 1.0
        
        # Reduce confidence for smaller sizes
        if executable_size < 50:
            confidence *= 0.8
        elif executable_size < 100:
            confidence *= 0.9
        
        # Reduce confidence for very tight spreads
        spread_a = snapshot_a.best_ask - snapshot_a.best_bid if snapshot_a.best_ask and snapshot_a.best_bid else 0
        spread_b = snapshot_b.best_ask - snapshot_b.best_bid if snapshot_b.best_ask and snapshot_b.best_bid else 0
        
        if spread_a < 0.01 or spread_b < 0.01:  # Very tight spreads
            confidence *= 0.7
        
        # Reduce confidence for high costs
        if total_cost > 0.98:  # Very high cost
            confidence *= 0.6
        
        return max(0.0, min(1.0, confidence))
    
    async def get_active_signals(self, limit: int = 100) -> List[ArbitrageSignals]:
        """Get active arbitrage signals."""
        db = next(get_db())
        
        try:
            signals = db.query(ArbitrageSignals).filter(
                ArbitrageSignals.status == "active",
                ArbitrageSignals.is_arbitrage == True,
                ArbitrageSignals.expires_at > datetime.utcnow()
            ).order_by(
                ArbitrageSignals.signal_strength.desc(),
                ArbitrageSignals.created_at.desc()
            ).limit(limit).all()
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting active signals: {e}")
            return []
        finally:
            db.close()
    
    async def cleanup_expired_signals(self) -> int:
        """Clean up expired arbitrage signals."""
        db = next(get_db())
        
        try:
            expired_count = db.query(ArbitrageSignals).filter(
                ArbitrageSignals.expires_at < datetime.utcnow()
            ).update({"status": "expired"})
            
            db.commit()
            
            if expired_count > 0:
                self.logger.info(f"Marked {expired_count} signals as expired")
            
            return expired_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired signals: {e}")
            db.rollback()
            return 0
        finally:
            db.close()


# Global instance
arbitrage_engine = ArbitrageEngine()
