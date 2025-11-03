"""PydanticAI model configuration."""

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings

# Create PydanticAI model using OpenAI-compatible endpoint from Hugging Face Space
# The model name will be sent in the request, but the actual model is determined by the HF Space
# Note: max_tokens will be set at the Agent level, not here
finance_model = OpenAIModel(
    model_name="gpt-3.5-turbo",  # Model name for API compatibility (HF Space will use its own model)
    provider=OpenAIProvider(
        base_url=f"{settings.hf_space_url}/v1",
        api_key=settings.api_key,
    ),
)

