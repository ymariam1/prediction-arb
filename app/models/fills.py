from sqlalchemy import Column, String, ForeignKey, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Fills(Base, TimestampMixin, UUIDMixin):
    """Model for storing order fills."""
    
    __tablename__ = "fills"
    
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    venue_fill_id = Column(String(200), nullable=True)  # Venue's fill identifier
    fill_price = Column(Float, nullable=False)  # Actual fill price
    fill_size = Column(Float, nullable=False)  # Actual fill size
    fill_time = Column(DateTime, nullable=False)  # When the fill occurred
    fees = Column(Float, nullable=False, default=0.0)  # Trading fees
    fill_metadata = Column(Text, nullable=True)  # JSON string for additional fill data
    
    # Relationships
    order = relationship("Orders", backref="fills")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index('idx_order_id', 'order_id'),
        Index('idx_fill_time', 'fill_time'),
    )
    
    def __repr__(self):
        return f"<Fills(order_id='{self.order_id}', fill_price={self.fill_price}, fill_size={self.fill_size})>"
