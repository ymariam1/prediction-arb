from sqlalchemy import Column, String, ForeignKey, Float, Boolean, JSON, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ArbitrageSignals(Base, TimestampMixin, UUIDMixin):
    """Model for storing arbitrage opportunities and signals."""
    
    __tablename__ = "arbitrage_signals"
    
    # Foreign keys
    pair_id = Column(String(36), ForeignKey("pairs.id"), nullable=False, index=True)
    market_a_id = Column(String(36), ForeignKey("canonical_market.id"), nullable=False, index=True)
    market_b_id = Column(String(36), ForeignKey("canonical_market.id"), nullable=False, index=True)
    
    # Arbitrage calculation results
    total_cost = Column(Float, nullable=False)  # C = total cost including fees and slippage
    edge_buffer = Column(Float, nullable=False)  # min_edge_buffer threshold
    is_arbitrage = Column(Boolean, nullable=False, default=False)  # C < 1 - min_edge_buffer
    executable_size = Column(Float, nullable=False)  # Maximum executable size
    
    # Market A (venue 1) details
    market_a_best_bid = Column(Float, nullable=True)  # Best bid price
    market_a_best_ask = Column(Float, nullable=True)  # Best ask price
    market_a_bid_size = Column(Float, nullable=True)  # Available bid size
    market_a_ask_size = Column(Float, nullable=True)  # Available ask size
    market_a_venue = Column(String(50), nullable=True)  # Venue name
    
    # Market B (venue 2) details  
    market_b_best_bid = Column(Float, nullable=True)
    market_b_best_ask = Column(Float, nullable=True)
    market_b_bid_size = Column(Float, nullable=True)
    market_b_ask_size = Column(Float, nullable=True)
    market_b_venue = Column(String(50), nullable=True)
    
    # Fee and slippage breakdown
    market_a_fees = Column(Float, nullable=False, default=0.0)  # Trading fees for market A
    market_b_fees = Column(Float, nullable=False, default=0.0)  # Trading fees for market B
    slippage_buffer = Column(Float, nullable=False, default=0.0)  # Slippage buffer applied
    
    # Execution strategy
    strategy = Column(String(50), nullable=False)  # "straddle", "long_short", etc.
    direction_a = Column(String(10), nullable=False)  # "buy" or "sell" for market A
    direction_b = Column(String(10), nullable=False)  # "buy" or "sell" for market B
    
    # Signal metadata
    signal_strength = Column(Float, nullable=False)  # Signal strength (0-1)
    confidence = Column(Float, nullable=False)  # Confidence in the signal (0-1)
    status = Column(String(50), nullable=False, default="active")  # active, expired, executed
    expires_at = Column(DateTime, nullable=True)  # When the signal expires
    
    # Additional metadata
    calculation_metadata = Column(JSON, nullable=True)  # Additional calculation details
    
    # Relationships
    pair = relationship("Pairs", backref="arbitrage_signals")
    market_a = relationship("CanonicalMarket", foreign_keys=[market_a_id], backref="signals_as_a")
    market_b = relationship("CanonicalMarket", foreign_keys=[market_b_id], backref="signals_as_b")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_arbitrage_signals_pair', 'pair_id'),
        Index('idx_arbitrage_signals_status', 'status'),
        Index('idx_arbitrage_signals_arbitrage', 'is_arbitrage'),
        Index('idx_arbitrage_signals_expires', 'expires_at'),
        Index('idx_arbitrage_signals_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ArbitrageSignals(pair='{self.pair_id}', arbitrage={self.is_arbitrage}, cost={self.total_cost:.4f})>"
