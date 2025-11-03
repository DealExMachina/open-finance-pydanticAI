"""PydanticAI agents for finance questions."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model
from app.config import settings


class FinanceAnswer(BaseModel):
    """Response model for finance questions."""
    answer: str = Field(description="The answer to the finance question in French")
    confidence: float = Field(description="Confidence level between 0 and 1", ge=0.0, le=1.0)
    key_terms: list[str] = Field(description="List of key financial terms mentioned in the answer")


# Model settings for reasoning models
# Qwen3 uses <think> tags which consume 40-60% of tokens
# Increase max_tokens to allow complete responses
agent_model_settings = ModelSettings(
    max_output_tokens=settings.max_tokens,
)

# Create agent for French finance questions
# Note: output_type will be specified at runtime in the endpoint
# Note: max_tokens is set via model_settings for reasoning models (<think> tags)
finance_agent = Agent(
    finance_model,
    model_settings=agent_model_settings,
    system_prompt=(
        "Vous êtes un assistant financier expert spécialisé dans la terminologie "
        "financière française. Répondez TOUJOURS en français, de manière claire, "
        "précise et concise. Fournissez des explications complètes mais sans "
        "développements excessifs.\n\n"
        "Pour chaque réponse, identifiez les termes clés financiers mentionnés "
        "et estimez votre niveau de confiance dans la réponse (entre 0 et 1).\n\n"
        "Note: Vous avez suffisamment de tokens (max_tokens={}) pour fournir des réponses complètes "
        "incluant votre raisonnement.".format(settings.max_tokens)
    ),
)

