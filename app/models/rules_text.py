from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class RulesText(Base, TimestampMixin, UUIDMixin):
    """Model for storing raw market rules text from venues."""
    
    __tablename__ = "rules_text"
    
    venue_id = Column(String(36), ForeignKey("venue.id"), nullable=False, index=True)
    market_id = Column(String(200), nullable=False, index=True)  # Venue's market identifier
    rules_text = Column(Text, nullable=False)  # Raw rules text from venue
    resolution_date = Column(DateTime, nullable=True)  # When the market resolves
    market_status = Column(String(50), nullable=False, default="active")  # active, resolved, cancelled
    version = Column(String(20), nullable=False, default="1.0")  # Version of the rules
    
    # Relationships
    venue = relationship("Venue", backref="rules_texts")
    
    # Composite index for efficient venue + market_id lookups
    __table_args__ = (
        Index('idx_venue_market_version', 'venue_id', 'market_id', 'version'),
    )
    
    def __repr__(self):
        return f"<RulesText(venue='{self.venue.name}', market_id='{self.market_id}', version='{self.version}')>"
