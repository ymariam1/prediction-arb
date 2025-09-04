from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, TimestampMixin, UUIDMixin):
    """Model for user authentication and management."""
    
    __tablename__ = "users"
    
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), nullable=False, default="viewer")  # viewer, trader, admin
    profile_data = Column(Text, nullable=True)  # JSON string for additional profile info
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', role='{self.role}')>"
