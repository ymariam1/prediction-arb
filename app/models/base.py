from sqlalchemy import Column, DateTime, func, String
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    """Mixin to add UUID primary key to models."""
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
