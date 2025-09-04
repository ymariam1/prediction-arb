from sqlalchemy import Column, String, ForeignKey, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, TimestampMixin, UUIDMixin):
    """Model for storing immutable audit trail of all system decisions and actions."""
    
    __tablename__ = "audit_log"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # Null for system actions
    action_type = Column(String(100), nullable=False, index=True)  # 'order_placed', 'fill_received', 'arbitrage_detected', etc.
    entity_type = Column(String(100), nullable=False, index=True)  # 'order', 'fill', 'position', 'market', etc.
    entity_id = Column(String(36), nullable=True, index=True)  # ID of the affected entity
    description = Column(Text, nullable=False)  # Human-readable description of the action
    action_metadata = Column(JSON, nullable=True)  # Structured data about the action
    ip_address = Column(String(45), nullable=True)  # IP address of the user (for user actions)
    user_agent = Column(Text, nullable=True)  # User agent string (for user actions)
    
    # Relationships
    user = relationship("User", backref="audit_logs")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index('idx_action_type', 'action_type'),
        Index('idx_entity_type_id', 'entity_type', 'entity_id'),
        Index('idx_audit_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action_type}', entity='{self.entity_type}', description='{self.description[:50]}...')>"
