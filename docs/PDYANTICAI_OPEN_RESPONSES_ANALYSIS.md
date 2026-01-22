# PydanticAI and Langfuse Support for Open Response Standard - Analysis

## Executive Summary

**PydanticAI** provides **partial support** for vLLM's Open Response Standard through:
- `UsageBase` class for token tracking
- `ModelResponse.provider_details` dictionary for provider-specific metadata
- Enhanced details may be accessible through `provider_details` if vLLM includes them

**Langfuse** supports flexible token usage tracking with arbitrary usage types, but **does not natively parse** vLLM's structured `InputTokensDetails`/`OutputTokensDetails`. Enhanced details can be manually extracted and passed to Langfuse via the usage parameter.

## PydanticAI Models for Open Response Standard

### OpenAIResponsesModel vs OpenAIChatModel

PydanticAI provides **two different model classes** for OpenAI-compatible APIs:

1. **`OpenAIChatModel`** (currently used in this project)
   - Uses OpenAI's **Chat Completions API** (`/v1/chat/completions`)
   - Standard request/response format
   - Token tracking via `UsageBase`

2. **`OpenAIResponsesModel`** (for Open Response Standard)
   - Uses OpenAI's **Responses API** (`/v1/responses`)
   - Implements the **Open Responses specification** (openresponses.org)
   - Better support for enhanced token details, reasoning, and streaming events
   - Native support for agentic loops and tool calling

### ModelResponse Class

PydanticAI's `ModelResponse` (from `pydantic_ai.models`) contains:
- **parts**: Sequence of response parts (TextPart, ToolCallPart, ThinkingPart)
- **usage**: `UsageBase` object for token tracking
- **model_name**: Name of the model used
- **timestamp**: When the response was generated
- **provider_name**: Name of the provider (e.g., "openai")
- **provider_details**: Dictionary containing provider-specific metadata ⭐ **Key for Open Response Standard**
- **provider_response_id**: Unique identifier from the provider
- **finish_reason**: Why the model stopped generating

### UsageBase Class Structure

PydanticAI's `UsageBase` class (from `pydantic_ai.usage`) provides:

**Standard Fields:**
- `input_tokens` (int): Number of input/prompt tokens
- `output_tokens` (int): Number of output/completion tokens
- `cache_write_tokens` (int): Tokens written to cache
- `cache_read_tokens` (int): Tokens read from cache
- `input_audio_tokens` (int): Audio input tokens
- `output_audio_tokens` (int): Audio output tokens
- `cache_audio_read_tokens` (int): Audio tokens read from cache

**Extended Details:**
- `details` (dict[str, int]): Model-specific information dictionary
  - Defaults to empty dict `{}`
  - Can store any extra details returned by the model
  - Included in OpenTelemetry attributes with `'gen_ai.usage.details.'` prefix

### Access Pattern in Current Codebase

```python
# Current usage extraction pattern
result = await agent.run(prompt)
usage = result.usage()
input_tokens = usage.input_tokens
output_tokens = usage.output_tokens
total_tokens = usage.total_tokens  # Computed property
cache_read = usage.cache_read_tokens
cache_write = usage.cache_write_tokens

# Access provider_details from ModelResponse
if hasattr(result, 'model_response'):
    model_resp = result.model_response
    provider_details = model_resp.provider_details  # Dict with provider-specific info
    # Enhanced token details may be here if vLLM includes them
```

## vLLM Open Response Standard Requirements

### InputTokensDetails Structure

```python
class InputTokensDetails:
    cached_tokens: int
    input_tokens_per_turn: list[int]
    cached_tokens_per_turn: list[int]
```

### OutputTokensDetails Structure

```python
class OutputTokensDetails:
    reasoning_tokens: int = 0
    tool_output_tokens: int = 0
    output_tokens_per_turn: list[int]
    tool_output_tokens_per_turn: list[int]
```

## Version Information

- **Current PydanticAI Version**: 1.44.0 (latest stable, upgraded from 1.39.0) ✅
- **Release Date**: January 16, 2026
- **Key Features in 1.44.0**:
  - Exa search tools integration
  - Bedrock Nova 2.0 Code Interpreter support
  - Fixed `WrapperModel` token counting
- **OpenAIResponsesModel**: ✅ Available in `pydantic_ai.models.openai`

## Compatibility Analysis

### ✅ Supported Features

1. **Basic Token Counts**: ✅ Fully supported
   - `input_tokens` → `usage.input_tokens`
   - `output_tokens` → `usage.output_tokens`

2. **Cache Tokens**: ✅ Supported
   - `cached_tokens` → `usage.cache_read_tokens` (if vLLM maps correctly)
   - Cache write tracking available via `usage.cache_write_tokens`

3. **Model-Specific Details**: ⚠️ Partially supported
   - Enhanced details may be in `usage.details` dict
   - Requires manual parsing and type checking

### ❌ Not Directly Supported

1. **Per-Turn Breakdowns**: ❌ Not directly supported
   - `input_tokens_per_turn` → Not available as structured list
   - `output_tokens_per_turn` → Not available as structured list
   - `cached_tokens_per_turn` → Not available as structured list
   - `tool_output_tokens_per_turn` → Not available as structured list

2. **Reasoning Tokens**: ❌ Not directly supported
   - `reasoning_tokens` → Not a standard field
   - May be in `usage.details` if vLLM includes it

3. **Tool Output Tokens**: ❌ Not directly supported
   - `tool_output_tokens` → Not a standard field
   - May be in `usage.details` if vLLM includes it

## Implementation Strategy

### Option 0: Switch to OpenAIResponsesModel (Recommended for Full Support)

**Best approach**: Use `OpenAIResponsesModel` instead of `OpenAIChatModel` to get native Open Response Standard support:

```python
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

# Create Responses API model
model = OpenAIResponsesModel(
    model_name="DragonLLM/Qwen-Open-Finance-R-8B",
    provider=OpenAIProvider(
        base_url=f"{endpoint_url}/v1",  # vLLM supports /v1/responses
        api_key=settings.api_key,
    ),
)

agent = Agent(model)
```

**Benefits:**
- Native support for Open Response Standard
- Enhanced token tracking (InputTokensDetails, OutputTokensDetails)
- Better streaming event support
- Built-in tools (web search, code interpreter, etc.)

**Requirements:**
- vLLM server must support `/v1/responses` endpoint
- Check if vLLM exposes Responses API (may need configuration)

### Option 1: Parse from `provider_details` Dictionary (Fallback)

If vLLM includes enhanced token details in the response, they may be accessible via `ModelResponse.provider_details`:

```python
def extract_enhanced_token_details(usage) -> dict:
    """Extract enhanced token details from PydanticAI UsageBase."""
    details = {}
    
    # Standard fields
    details['input_tokens'] = usage.input_tokens
    details['output_tokens'] = usage.output_tokens
    details['cache_read_tokens'] = usage.cache_read_tokens
    details['cache_write_tokens'] = usage.cache_write_tokens
    
    # Enhanced details from details dict
    if usage.details:
        # Check for vLLM-specific keys
        if 'input_tokens_details' in usage.details:
            # May be serialized as dict or JSON string
            input_details = usage.details.get('input_tokens_details')
            if isinstance(input_details, dict):
                details['cached_tokens'] = input_details.get('cached_tokens', 0)
                details['input_tokens_per_turn'] = input_details.get('input_tokens_per_turn', [])
                details['cached_tokens_per_turn'] = input_details.get('cached_tokens_per_turn', [])
        
        if 'output_tokens_details' in usage.details:
            output_details = usage.details.get('output_tokens_details')
            if isinstance(output_details, dict):
                details['reasoning_tokens'] = output_details.get('reasoning_tokens', 0)
                details['tool_output_tokens'] = output_details.get('tool_output_tokens', 0)
                details['output_tokens_per_turn'] = output_details.get('output_tokens_per_turn', [])
                details['tool_output_tokens_per_turn'] = output_details.get('tool_output_tokens_per_turn', [])
    
    return details
```

### Option 2: Direct API Response Access

Access the raw OpenAI API response to extract enhanced details:

```python
# This would require accessing the underlying provider response
# May not be directly accessible through PydanticAI's abstraction
```

### Option 3: Custom Provider Extension

Create a custom provider wrapper that extracts enhanced details before PydanticAI processes them.

## Testing Plan

### 0. Test OpenAIResponsesModel Support

First, verify if vLLM supports the Responses API endpoint:

```python
# Test if vLLM exposes /v1/responses endpoint
import httpx

response = httpx.get("https://your-vllm-server/v1/responses", timeout=5.0)
# Should return 405 (Method Not Allowed) or 404 if not supported
# 200/401 means endpoint exists
```

If supported, test with OpenAIResponsesModel:

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIResponsesModel(
    model_name="DragonLLM/Qwen-Open-Finance-R-8B",
    provider=OpenAIProvider(
        base_url="https://your-vllm-server/v1",
        api_key="not-needed",
    ),
)

agent = Agent(model)
result = await agent.run("Test prompt")
# Check if enhanced token details are available
```

### 1. Verify vLLM Response Format (Chat Completions API)

Test if vLLM actually includes enhanced details in responses:

```python
# Test script
import asyncio
from app.models import get_finance_model
from pydantic_ai import Agent

async def test_enhanced_details():
    model = get_finance_model()
    agent = Agent(model)
    
    result = await agent.run("Test prompt")
    usage = result.usage()
    
    print("Standard fields:")
    print(f"  input_tokens: {usage.input_tokens}")
    print(f"  output_tokens: {usage.output_tokens}")
    print(f"  cache_read_tokens: {usage.cache_read_tokens}")
    print(f"  cache_write_tokens: {usage.cache_write_tokens}")
    
    print("\nDetails dict:")
    print(f"  {usage.details}")
    
    # Check for enhanced details
    if usage.details:
        print("\nEnhanced details keys:")
        for key in usage.details.keys():
            print(f"  {key}: {usage.details[key]}")

asyncio.run(test_enhanced_details())
```

### 2. Check Provider Response

Inspect the raw OpenAI-compatible response to see what vLLM actually returns.

## Recommendations

### Short Term (Current Implementation)

1. **Use Standard Fields**: Continue using `usage.input_tokens`, `usage.output_tokens`, `usage.cache_read_tokens`
2. **Inspect `details` Dict**: Test if vLLM includes enhanced details in `usage.details`
3. **Manual Parsing**: If details are present, create utility functions to extract them

### Medium Term (Enhanced Support)

1. **Create Utility Module**: `app/open_response_parser.py` to extract enhanced details
2. **Update Metrics Recording**: Enhance `app/logfire_metrics.py` to record per-turn breakdowns if available
3. **Update Observability**: Add enhanced metrics to Langfuse and Logfire integrations

### Long Term (Full Support)

1. **Feature Request**: Submit feature request to PydanticAI for native support of structured token details
2. **Custom Provider**: Consider creating a vLLM-specific provider extension if needed
3. **Upstream Contribution**: Contribute to PydanticAI if we develop a clean solution

## References

- [PydanticAI UsageBase API](https://ai.pydantic.dev/api/usage/)
- [PydanticAI OpenAI Provider](https://ai.pydantic.dev/models/openai/)
- [vLLM Open Response Protocol](https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/responses/protocol/)
- [GitHub Issue: Cache tokens in OTel](https://github.com/pydantic/pydantic-ai/issues/3181)

## Next Steps

1. ✅ **Test vLLM Response**: Run test script to see what vLLM actually returns
2. ✅ **Inspect `details` Dict**: Check if enhanced details are in `usage.details`
3. ⏳ **Create Parser Utility**: If details are available, create extraction utility
4. ⏳ **Update Metrics**: Enhance observability to use enhanced details
5. ⏳ **Document Findings**: Update implementation plan with test results
