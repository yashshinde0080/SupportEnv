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
    generator_provider: Optional[str] = Field(default=None, validation_alias=AliasChoices("GENERATOR_PROVIDER", "generator_provider")) # openai, gemini, groq, openrouter, ollama
    generator_model: Optional[str] = Field(default=None, validation_alias=AliasChoices("GENERATOR_MODEL", "generator_model"))
    
    # ===================
    # Gemini Configuration
    # ===================
    gemini_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"))
    gemini_model: Optional[str] = Field(default=None, validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model"))
    
    # ===================
    # Groq Configuration
    # ===================
    groq_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"))
    groq_model: Optional[str] = Field(default=None, validation_alias=AliasChoices("GROQ_MODEL", "groq_model"))
    
    # ===================
    # OpenRouter Configuration
    # ===================
    openrouter_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENROUTER_API_KEY", "openrouter_api_key"))
    openrouter_model: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENROUTER_MODEL", "openrouter_model"))
    
    # ===================
    # Ollama Configuration
    # ===================
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias=AliasChoices("OLLAMA_BASE_URL", "ollama_base_url"))
    ollama_model: Optional[str] = Field(default=None, validation_alias=AliasChoices("OLLAMA_MODEL", "ollama_model"))
    
    # ===================
    # OpenAI Configuration
    # ===================
    openai_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"))
    openai_model: str = Field(default="gpt-3.5-turbo", validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"))
    openai_temperature: float = Field(default=0.3, validation_alias=AliasChoices("OPENAI_TEMPERATURE", "openai_temperature"))
    openai_max_tokens: int = Field(default=200, validation_alias=AliasChoices("OPENAI_MAX_TOKENS", "openai_max_tokens"))
    
    # ===================
    # HuggingFace Configuration
    # ===================
    hf_token: Optional[str] = Field(default=None, validation_alias=AliasChoices("HF_TOKEN", "hf_token"))
    hf_space_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("HF_SPACE_URL", "hf_space_url"))
    hf_space_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("HF_SPACE_ID", "hf_space_id"))
    
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

    @property
    def generator_full_model(self) -> str:
        """Get the full model string for litellm, including provider prefix if needed."""
        if not self.generator_model:
            # Fallback to provider-specific defaults if model not set
            if self.generator_provider == "ollama":
                return f"ollama/{self.ollama_model}" if self.ollama_model else ""
            if self.generator_provider == "gemini":
                return f"gemini/{self.gemini_model}" if self.gemini_model else ""
            if self.generator_provider == "groq":
                return f"groq/{self.groq_model}" if self.groq_model else ""
            if self.generator_provider == "openrouter":
                return f"openrouter/{self.openrouter_model}" if self.openrouter_model else ""
            return self.openai_model or "gpt-3.5-turbo"
        
        # If model already has a slash, assume it already has provider
        if "/" in self.generator_model:
            return self.generator_model
        
        # Add provider prefix if specified and not openai
        if self.generator_provider and self.generator_provider.lower() != "openai":
            return f"{self.generator_provider.lower()}/{self.generator_model}"
        
        return self.generator_model

    def validate_llm_config(self):
        """
        Validate that LLM settings are correctly configured.
        Raises ValueError if configuration is invalid or uses placeholder keys.
        """
        if not self.use_llm_generator:
            return

        model = self.generator_full_model
        if not model:
            raise ValueError(
                "USE_LLM_GENERATOR is enabled but no model is configured. "
                "Please set GENERATOR_MODEL or GENERATOR_PROVIDER in your .env file."
            )

        # Check for placeholder keys
        def is_placeholder(key: Optional[str]) -> bool:
            if not key:
                return True
            placeholders = ["your-", "sk-your-", "replace-with-", "sk-proj-your"]
            return any(p in key.lower() for p in placeholders)

        # Extract provider from model string (e.g., 'ollama/llama2' -> 'ollama')
        provider = self.generator_provider.lower() if self.generator_provider else "openai"
        if "/" in model:
            provider = model.split("/")[0].lower()

        if provider == "openai":
            if is_placeholder(self.openai_api_key):
                raise ValueError("OpenAI API key is missing or is a placeholder in .env (OPENAI_API_KEY).")
        elif provider == "gemini":
            if is_placeholder(self.gemini_api_key):
                raise ValueError("Gemini API key is missing or is a placeholder in .env (GEMINI_API_KEY).")
        elif provider == "groq":
            if is_placeholder(self.groq_api_key):
                raise ValueError("Groq API key is missing or is a placeholder in .env (GROQ_API_KEY).")
        elif provider == "openrouter":
            if is_placeholder(self.openrouter_api_key):
                raise ValueError("OpenRouter API key is missing or is a placeholder in .env (OPENROUTER_API_KEY).")
        elif provider == "ollama":
            if not self.ollama_base_url:
                raise ValueError("Ollama base URL is not configured in .env (OLLAMA_BASE_URL).")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Convenience function
settings = get_settings()