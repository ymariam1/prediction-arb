from sqlalchemy import Column, String, ForeignKey, Float, Integer, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Orders(Base, TimestampMixin, UUIDMixin):
    """Model for storing trading orders."""
    
    __tablename__ = "orders"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    venue_id = Column(String(36), ForeignKey("venue.id"), nullable=False, index=True)
    market_id = Column(String(200), nullable=False, index=True)  # Venue's market identifier
    side = Column(String(10), nullable=False, index=True)  # 'buy' or 'sell'
    order_type = Column(String(20), nullable=False)  # 'market', 'limit', 'ioc', 'fok'
    size = Column(Float, nullable=False)  # Order size
    price = Column(Float, nullable=True)  # Limit price (null for market orders)
    time_in_force = Column(String(10), nullable=False)  # 'ioc', 'fok', 'gtc'
    status = Column(String(20), nullable=False, default="pending")  # pending, filled, cancelled, rejected
    venue_order_id = Column(String(200), nullable=True)  # Venue's order identifier
    order_metadata = Column(Text, nullable=True)  # JSON string for additional order data
    
    # Relationships
    user = relationship("User", backref="orders")
    venue = relationship("Venue", backref="orders")
    
    # Composite indexes for efficient lookups
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_venue_market_status', 'venue_id', 'market_id', 'status'),
        Index('idx_orders_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Orders(user='{self.user.username}', venue='{self.venue.name}', market='{self.market_id}', side='{self.side}', size={self.size})>"
