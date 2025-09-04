from sqlalchemy import Column, String, ForeignKey, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Settlements(Base, TimestampMixin, UUIDMixin):
    """Model for storing market settlements and final outcomes."""
    
    __tablename__ = "settlements"
    
    venue_id = Column(String(36), ForeignKey("venue.id"), nullable=False, index=True)
    market_id = Column(String(200), nullable=False, index=True)  # Venue's market identifier
    outcome = Column(String(200), nullable=False)  # Final outcome/result
    settlement_price = Column(Float, nullable=False)  # Final settlement price
    settlement_time = Column(DateTime, nullable=False)  # When settlement occurred
    resolution_notes = Column(Text, nullable=True)  # Notes about the resolution
    settlement_metadata = Column(Text, nullable=True)  # JSON string for additional settlement data
    
    # Relationships
    venue = relationship("Venue", backref="settlements")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index('idx_settlements_venue_market', 'venue_id', 'market_id'),
        Index('idx_settlement_time', 'settlement_time'),
    )
    
    def __repr__(self):
        return f"<Settlements(venue='{self.venue.name}', market='{self.market_id}', outcome='{self.outcome}', price={self.settlement_price})>"
