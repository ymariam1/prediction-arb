from sqlalchemy import Column, String, Boolean, Text
from app.models.base import Base, TimestampMixin, UUIDMixin


class Venue(Base, TimestampMixin, UUIDMixin):
    """Model for prediction market venues (Kalshi, Polymarket, etc.)."""
    
    __tablename__ = "venue"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    api_base_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    venue_type = Column(String(50), nullable=False)  # 'prediction_market', 'exchange', etc.
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Venue(name='{self.name}', type='{self.venue_type}')>"
