from sqlalchemy import Column, String, ForeignKey, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Positions(Base, TimestampMixin, UUIDMixin):
    """Model for storing user positions across venues."""
    
    __tablename__ = "positions"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    venue_id = Column(String(36), ForeignKey("venue.id"), nullable=False, index=True)
    market_id = Column(String(200), nullable=False, index=True)  # Venue's market identifier
    size = Column(Float, nullable=False)  # Position size (positive = long, negative = short)
    avg_price = Column(Float, nullable=False)  # Average entry price
    unrealized_pnl = Column(Float, nullable=False, default=0.0)  # Unrealized profit/loss
    realized_pnl = Column(Float, nullable=False, default=0.0)  # Realized profit/loss
    last_updated = Column(DateTime, nullable=False)  # Last position update time
    position_metadata = Column(Text, nullable=True)  # JSON string for additional position data
    
    # Relationships
    user = relationship("User", backref="positions")
    venue = relationship("Venue", backref="positions")
    
    # Composite indexes for efficient lookups
    __table_args__ = (
        Index('idx_user_venue', 'user_id', 'venue_id'),
        Index('idx_positions_venue_market', 'venue_id', 'market_id'),
        Index('idx_last_updated', 'last_updated'),
    )
    
    def __repr__(self):
        return f"<Positions(user='{self.user.username}', venue='{self.venue.name}', market='{self.market_id}', size={self.size})>"
