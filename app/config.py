"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


# Available endpoints
ENDPOINTS = {
    "koyeb": {
        "url": "https://dragon-llm-dealexmachina-673cae4f.koyeb.app",
        "model": "DragonLLM/Qwen-Open-Finance-R-8B",  # vLLM requires exact model name
    },
    "hf": {
        "url": "https://jeanbaptdzd-open-finance-llm-8b.hf.space",
        "model": "dragon-llm-open-finance",  # HF Space accepts any name
    },
}


class Settings(BaseSettings):
    """Application settings."""
    
    # Endpoint selection: "koyeb" or "hf"
    endpoint: str = "koyeb"
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the selected endpoint."""
        return ENDPOINTS.get(self.endpoint, ENDPOINTS["koyeb"])["url"]
    
    @property
    def model_name(self) -> str:
        """Get the model name for the selected endpoint."""
        return ENDPOINTS.get(self.endpoint, ENDPOINTS["koyeb"])["model"]
    
    # Legacy alias for compatibility
    @property
    def hf_space_url(self) -> str:
        return self.base_url
    
    # OpenAI-compatible API settings
    api_key: str = "not-needed"
    
    # API configuration
    timeout: float = 120.0
    max_retries: int = 3
    
    # Logfire configuration
    environment: str = "development"  # development, staging, production
    
    # Generation settings for reasoning models
    # Qwen3 uses <think> tags which consume 40-60% of tokens
    # Increase max_tokens to allow complete responses
    max_tokens: int = 1500  # Increased for reasoning models (was default ~800-1000)
    
    # Context window limits for Qwen-3 8B
    # Base context window: 32,768 tokens (32K)
    # Extended with YaRN: up to 128,000 tokens (128K)
    # Current max_tokens is for generation, context input can use up to ~30K tokens
    
    # Generation limits
    # Maximum theoretical generation: 20,000 tokens
    # Practical limit depends on: context_window - input_tokens - safety_margin
    # With typical input (~500 tokens), can generate up to ~30K tokens
    max_generation_limit: int = 20000  # Theoretical maximum (rarely needed)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

