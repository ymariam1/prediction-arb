from sqlalchemy import Column, String, ForeignKey, Float, Integer, DateTime, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class BookLevels(Base, TimestampMixin, UUIDMixin):
    """Model for storing order book levels from venues."""
    
    __tablename__ = "book_levels"
    
    venue_id = Column(String(36), ForeignKey("venue.id"), nullable=False, index=True)
    market_id = Column(String(200), nullable=False, index=True)  # Venue's market identifier
    side = Column(String(10), nullable=False, index=True)  # 'buy' or 'sell'
    level = Column(Integer, nullable=False)  # Price level (1 = best, 2 = second best, etc.)
    price = Column(Float, nullable=False)  # Price at this level
    size = Column(Float, nullable=False)  # Available size at this level
    timestamp = Column(DateTime, nullable=False, index=True)  # When this data was captured
    
    # Relationships
    venue = relationship("Venue", backref="book_levels")
    
    # Composite indexes for efficient lookups
    __table_args__ = (
        Index('idx_venue_market_side', 'venue_id', 'market_id', 'side'),
        Index('idx_venue_market_timestamp', 'venue_id', 'market_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<BookLevels(venue='{self.venue.name}', market='{self.market_id}', side='{self.side}', level={self.level}, price={self.price})>"
