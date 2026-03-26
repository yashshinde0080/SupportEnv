"""
Configuration management for SupportEnv.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ===================
    # Server Configuration
    # ===================
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=7860, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="info", env="LOG_LEVEL")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    # ===================
    # Environment Settings
    # ===================
    max_concurrent_envs: int = Field(default=100, env="MAX_CONCURRENT_ENVS")
    default_seed: int = Field(default=42, env="DEFAULT_SEED")
    
    # ===================
    # OpenAI Configuration
    # ===================
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.3, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=200, env="OPENAI_MAX_TOKENS")
    
    # ===================
    # HuggingFace Configuration
    # ===================
    hf_token: Optional[str] = Field(default=None, env="HF_TOKEN")
    hf_space_url: Optional[str] = Field(default=None, env="HF_SPACE_URL")
    hf_space_id: Optional[str] = Field(default=None, env="HF_SPACE_ID")
    
    # ===================
    # Environment URLs
    # ===================
    support_env_url: str = Field(
        default="http://localhost:7860", 
        env="SUPPORT_ENV_URL"
    )
    
    # ===================
    # Grading Configuration
    # ===================
    grading_strict_mode: bool = Field(default=True, env="GRADING_STRICT_MODE")
    grading_verbose: bool = Field(default=False, env="GRADING_VERBOSE")
    
    # ===================
    # Baseline Configuration
    # ===================
    baseline_seeds: str = Field(default="42,123,456", env="BASELINE_SEEDS")
    baseline_output_path: str = Field(
        default="baseline/results.json", 
        env="BASELINE_OUTPUT_PATH"
    )
    baseline_verbose: bool = Field(default=False, env="BASELINE_VERBOSE")
    
    # ===================
    # Logging
    # ===================
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: str = Field(default="logs/support_env.log", env="LOG_FILE")
    enable_file_logging: bool = Field(default=False, env="ENABLE_FILE_LOGGING")
    
    # ===================
    # Security
    # ===================
    api_secret_key: Optional[str] = Field(default=None, env="API_SECRET_KEY")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    
    # ===================
    # Rate Limiting
    # ===================
    rate_limit_enabled: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    # ===================
    # Computed Properties
    # ===================
    
    @property
    def baseline_seeds_list(self) -> List[int]:
        """Parse baseline seeds string into list of integers."""
        return [int(s.strip()) for s in self.baseline_seeds.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.openai_api_key is not None and len(self.openai_api_key) > 0


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Convenience function
settings = get_settings()