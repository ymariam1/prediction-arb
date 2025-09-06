from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Database
    database_url: str = "sqlite:///./prediction_arb.db"
    database_echo: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Prediction Market Arbitrage System"
    
    # Venues
    kalshi_api_key_id: Optional[str] = None
    kalshi_api_private_key: Optional[str] = None
    polymarket_api_key: Optional[str] = None
    polymarket_api_secret: Optional[str] = None
    polymarket_api_passphrase: Optional[str] = None
    
    # LLM Services
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # openai, anthropic
    llm_model: str = "o3-mini"  # o3-mini, o3, gpt-4, gpt-3.5-turbo, claude-3-haiku, qwen-turbo, kimi-chat, etc.
    llm_temperature: float = 0.1  # Low temperature for consistent results
    llm_max_tokens: int = 4000  # Increased for O3 chain-of-thought reasoning
    
    # Development
    debug: Optional[str] = None
    log_level: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
