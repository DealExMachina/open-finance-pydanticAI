"""PydanticAI model configuration."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings

# Import vLLM provider for Koyeb endpoint
if settings.api_endpoint.lower() == "koyeb":
    from app.providers.vllm_provider import VLLMProvider
    ProviderClass = VLLMProvider
else:
    ProviderClass = OpenAIProvider

# Get base URL from settings (automatically selects based on api_endpoint)
base_url = settings.base_url
endpoint_name = "Koyeb vLLM" if settings.api_endpoint.lower() == "koyeb" else "Hugging Face Space"

# Model name: Use actual model name for Koyeb, placeholder for HF Space
# Koyeb vLLM requires the exact model name, HF Space uses a placeholder
if settings.api_endpoint.lower() == "koyeb":
    model_name = settings.model_name  # "DragonLLM/Qwen-Open-Finance-R-8B"
else:
    model_name = "dragon-llm-open-finance"  # Placeholder for HF Space

# Create PydanticAI model using OpenAI-compatible endpoint
# Use VLLMProvider for Koyeb (handles structured outputs conversion)
# Use OpenAIProvider for HF Space (standard tool calling)
finance_model = OpenAIChatModel(
    model_name=model_name,
    provider=ProviderClass(
        base_url=base_url,
        api_key=settings.api_key,
    ),
)

# Log which endpoint is being used (for debugging)
print(f"📡 Using {endpoint_name} endpoint: {base_url}")
if settings.api_endpoint.lower() == "koyeb":
    print("   ✅ vLLM structured outputs conversion enabled")

