"""
Configuration management for SupportEnv.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from functools import lru_cache
import dotenv
dotenv.load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )
    
    # ===================
    # Server Configuration
    # ===================
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HOST", "host"))
    port: int = Field(default=7860, validation_alias=AliasChoices("PORT", "port"))
    workers: int = Field(default=1, validation_alias=AliasChoices("WORKERS", "workers"))
    debug: bool = Field(default=False, validation_alias=AliasChoices("DEBUG", "debug"))
    log_level: str = Field(default="info", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))
    environment: str = Field(default="production", validation_alias=AliasChoices("ENVIRONMENT", "environment"))
    
    # ===================
    # Environment Settings
    # ===================
    max_concurrent_envs: int = Field(default=100, validation_alias=AliasChoices("MAX_CONCURRENT_ENVS", "max_concurrent_envs"))
    default_seed: int = Field(default=42, validation_alias=AliasChoices("DEFAULT_SEED", "default_seed"))
    
    # ===================
    # LLM Settings
    # ===================
    use_llm_generator: bool = Field(default=False, validation_alias=AliasChoices("USE_LLM_GENERATOR", "use_llm_generator"))
    generator_provider: str = Field(default=os.getenv("GENERATOR_PROVIDER"), validation_alias=AliasChoices("GENERATOR_PROVIDER", "generator_provider")) # openai, gemini, groq, openrouter, ollama
    generator_model: Optional[str] = Field(default=os.getenv("GENERATOR_MODEL"), validation_alias=AliasChoices("GENERATOR_MODEL", "generator_model"))
    
    # ===================
    # Gemini Configuration
    # ===================
    gemini_api_key: Optional[str] = Field(default=os.getenv("GEMINI_API_KEY"), validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"))
    gemini_model: str = Field(default=os.getenv("GEMINI_MODEL"), validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model"))
    
    # ===================
    # Groq Configuration
    # ===================
    groq_api_key: Optional[str] = Field(default=os.getenv("GROQ_API_KEY"), validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"))
    groq_model: str = Field(default=os.getenv("GROQ_MODEL"), validation_alias=AliasChoices("GROQ_MODEL", "groq_model"))
    
    # ===================
    # OpenRouter Configuration
    # ===================
    openrouter_api_key: Optional[str] = Field(default=os.getenv("OPENROUTER_API_KEY"), validation_alias=AliasChoices("OPENROUTER_API_KEY", "openrouter_api_key"))
    openrouter_model: str = Field(default=os.getenv("OPENROUTER_MODEL"), validation_alias=AliasChoices("OPENROUTER_MODEL", "openrouter_model"))
    
    # ===================
    # Ollama Configuration
    # ===================
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias=AliasChoices("OLLAMA_BASE_URL", "ollama_base_url"))
    ollama_model: str = Field(default=os.getenv("OLLAMA_MODEL"), validation_alias=AliasChoices("OLLAMA_MODEL", "ollama_model"))
    
    # ===================
    # OpenAI Configuration
    # ===================
    openai_api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY"), validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"))
    openai_model: str = Field(default=os.getenv("OPENAI_MODEL"), validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"))
    openai_temperature: float = Field(default=0.3, validation_alias=AliasChoices("OPENAI_TEMPERATURE", "openai_temperature"))
    openai_max_tokens: int = Field(default=200, validation_alias=AliasChoices("OPENAI_MAX_TOKENS", "openai_max_tokens"))
    
    # ===================
    # HuggingFace Configuration
    # ===================
    hf_token: Optional[str] = Field(default=os.getenv("HF_TOKEN"), validation_alias=AliasChoices("HF_TOKEN", "hf_token"))
    hf_space_url: Optional[str] = Field(default=os.getenv("HF_SPACE_URL"), validation_alias=AliasChoices("HF_SPACE_URL", "hf_space_url"))
    hf_space_id: Optional[str] = Field(default=os.getenv("HF_SPACE_ID"), validation_alias=AliasChoices("HF_SPACE_ID", "hf_space_id"))
    
    # ===================
    # Environment URLs
    # ===================
    support_env_url: str = Field(
        default="http://localhost:7860", 
        validation_alias=AliasChoices("SUPPORT_ENV_URL", "support_env_url")
    )
    
    # ===================
    # Grading Configuration
    # ===================
    grading_strict_mode: bool = Field(default=True, validation_alias=AliasChoices("GRADING_STRICT_MODE", "grading_strict_mode"))
    grading_verbose: bool = Field(default=False, validation_alias=AliasChoices("GRADING_VERBOSE", "grading_verbose"))
    
    # ===================
    # Baseline Configuration
    # ===================
    baseline_seeds: str = Field(default="42,123,456", validation_alias=AliasChoices("BASELINE_SEEDS", "baseline_seeds"))
    baseline_output_path: str = Field(
        default="baseline/results.json", 
        validation_alias=AliasChoices("BASELINE_OUTPUT_PATH", "baseline_output_path")
    )
    baseline_verbose: bool = Field(default=False, validation_alias=AliasChoices("BASELINE_VERBOSE", "baseline_verbose"))
    
    # ===================
    # Logging
    # ===================
    log_format: str = Field(default="json", validation_alias=AliasChoices("LOG_FORMAT", "log_format"))
    log_file: str = Field(default="logs/support_env.log", validation_alias=AliasChoices("LOG_FILE", "log_file"))
    enable_file_logging: bool = Field(default=False, validation_alias=AliasChoices("ENABLE_FILE_LOGGING", "enable_file_logging"))
    
    # ===================
    # Security
    # ===================
    api_secret_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("API_SECRET_KEY", "api_secret_key"))
    cors_origins: str = Field(default="*", validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"))
    
    # ===================
    # Rate Limiting
    # ===================
    rate_limit_enabled: bool = Field(default=False, validation_alias=AliasChoices("RATE_LIMIT_ENABLED", "rate_limit_enabled"))
    rate_limit_requests: int = Field(default=100, validation_alias=AliasChoices("RATE_LIMIT_REQUESTS", "rate_limit_requests"))
    rate_limit_window: int = Field(default=60, validation_alias=AliasChoices("RATE_LIMIT_WINDOW", "rate_limit_window"))

    
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

    @property
    def has_gemini_key(self) -> bool:
        """Check if Gemini API key is configured."""
        return self.gemini_api_key is not None and len(self.gemini_api_key) > 0

    @property
    def has_groq_key(self) -> bool:
        """Check if Groq API key is configured."""
        return self.groq_api_key is not None and len(self.groq_api_key) > 0

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return self.openrouter_api_key is not None and len(self.openrouter_api_key) > 0


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Convenience function
settings = get_settings()