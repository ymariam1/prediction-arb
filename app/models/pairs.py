from sqlalchemy import Column, String, ForeignKey, Float, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Pairs(Base, TimestampMixin, UUIDMixin):
    """Model for storing matched market pairs for arbitrage opportunities."""
    
    __tablename__ = "pairs"
    
    market_a_id = Column(String(36), ForeignKey("canonical_market.id"), nullable=False, index=True)
    market_b_id = Column(String(36), ForeignKey("canonical_market.id"), nullable=False, index=True)
    equivalence_score = Column(Float, nullable=False)  # LLM-generated equivalence score (0-1)
    conflict_list = Column(JSON, nullable=True)  # List of identified conflicts
    hard_ok = Column(Boolean, nullable=False, default=False)  # Whether hard constraints are satisfied
    confidence = Column(Float, nullable=False)  # Confidence in the pairing (0-1)
    status = Column(String(50), nullable=False, default="active")  # active, inactive, flagged
    
    # Relationships
    market_a = relationship("CanonicalMarket", foreign_keys=[market_a_id], backref="pairs_as_a")
    market_b = relationship("CanonicalMarket", foreign_keys=[market_b_id], backref="pairs_as_b")
    
    # Composite index for efficient pair lookups
    __table_args__ = (
        Index('idx_market_pair', 'market_a_id', 'market_b_id'),
        Index('idx_equivalence_score', 'equivalence_score'),
    )
    
    def __repr__(self):
        return f"<Pairs(market_a='{self.market_a.canonical_id}', market_b='{self.market_b.canonical_id}', score={self.equivalence_score})>"
