# Open Finance PydanticAI

Open Finance API using PydanticAI for LLM inference, connecting to Hugging Face Space.

## Overview

This application uses PydanticAI to interact with the OpenAI-compatible API exposed by the Hugging Face Space `jeanbaptdzd/open-finance-llm-8b`. The model (`DragonLLM/qwen3-8b-fin-v1.0`) is specialized in French financial terminology.

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the API
uvicorn app.main:app --reload
```

## Configuration

The application is configured to connect to:
- **Hugging Face Space**: `https://jeanbaptdzd-open-finance-llm-8b.hf.space`
- **Model**: `DragonLLM/qwen3-8b-fin-v1.0`
- **No authentication required** (no token gating)

You can customize these settings via environment variables or `.env` file:
- `HF_SPACE_URL`: Hugging Face Space URL
- `API_KEY`: API key (not required, defaults to "not-needed")
- `MODEL_NAME`: Model name

## API Endpoints

### `GET /`
Root endpoint with service information.

### `GET /health`
Health check endpoint.

### `POST /ask`
Ask a finance question to the AI agent.

**Request:**
```json
{
  "question": "Qu'est-ce qu'une date de valeur?"
}
```

**Response:**
```json
{
  "answer": "Une date de valeur est...",
  "confidence": 0.95,
  "key_terms": ["date de valeur", "opération bancaire", "crédit"]
}
```

## Development

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy app
```

## Architecture

- `app/config.py`: Application settings and configuration
- `app/models.py`: PydanticAI model configuration (connects to HF Space)
- `app/agents.py`: PydanticAI agents for finance questions
- `app/main.py`: FastAPI application with endpoints

