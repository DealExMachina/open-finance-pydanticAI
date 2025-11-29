"""PydanticAI model configuration."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings

# Create PydanticAI model using OpenAI-compatible endpoint
# Supports both Koyeb (vLLM) and HF Space (Transformers) backends
# Configure via ENDPOINT env var: "koyeb" (default) or "hf"
finance_model = OpenAIChatModel(
    model_name=settings.model_name,
    provider=OpenAIProvider(
        base_url=f"{settings.base_url}/v1",
        api_key=settings.api_key,
    ),
)

