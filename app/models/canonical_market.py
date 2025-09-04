from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class CanonicalMarket(Base, TimestampMixin, UUIDMixin):
    """Model for canonical, normalized market data."""
    
    __tablename__ = "canonical_market"
    
    rules_text_id = Column(String(36), ForeignKey("rules_text.id"), nullable=False, index=True)
    canonical_id = Column(String(200), nullable=False, unique=True, index=True)  # Our canonical identifier
    question_text = Column(Text, nullable=False)  # Normalized question text
    outcome_options = Column(JSON, nullable=False)  # List of possible outcomes
    resolution_criteria = Column(JSON, nullable=False)  # Structured resolution criteria
    category = Column(String(100), nullable=True, index=True)  # Market category
    tags = Column(JSON, nullable=True)  # Array of tags for classification
    
    # Relationships
    rules_text = relationship("RulesText", backref="canonical_markets")
    
    def __repr__(self):
        return f"<CanonicalMarket(canonical_id='{self.canonical_id}', question='{self.question_text[:50]}...')>"
