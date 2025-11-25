# vLLM Integration for PydanticAI

## Overview

This document explains how vLLM structured outputs are integrated with PydanticAI's `output_type` feature.

## Problem

- **PydanticAI** uses tool calling (`tools` + `tool_choice="required"`) for structured outputs
- **vLLM** uses `extra_body.structured_outputs` for structured outputs
- These are incompatible formats

## Solution

A custom `VLLMProvider` was created that:

1. **Detects vLLM endpoints** automatically (koyeb, vllm, localhost:8000)
2. **Intercepts tool-based requests** when `tool_choice="required"` and exactly one tool
3. **Converts to vLLM format**: Extracts JSON schema from tool parameters → `extra_body.structured_outputs`
4. **Converts response back**: vLLM's JSON-in-content → tool call format expected by PydanticAI

## Implementation

### Files

- `app/providers/vllm_provider.py` - Custom VLLMProvider class
- `app/models.py` - Uses VLLMProvider for Koyeb, OpenAIProvider for HF Space

### How It Works

```python
# PydanticAI sends:
{
  "tools": [{"function": {"name": "...", "parameters": {...}}}],
  "tool_choice": "required"
}

# VLLMProvider converts to:
{
  "extra_body": {
    "structured_outputs": {
      "json": {...}  # JSON schema from tool parameters
    }
  }
}

# vLLM returns JSON in message.content
# VLLMProvider converts back to tool call format
```

## Usage

No code changes needed! The provider is automatically selected based on `API_ENDPOINT`:

```python
# .env
API_ENDPOINT=koyeb  # Uses VLLMProvider
# or
API_ENDPOINT=hf     # Uses OpenAIProvider
```

## Test Results

With vLLM endpoint (Koyeb):
- ✅ Test 1: Complete success
- ✅ Test 2: Complete success  
- ⚠️  Test 3: Partial success (model limitation, not conversion issue)

**Result: 2/3 complete success, 1/3 partial (67% complete)**

## Technical Details

### vLLM Structured Outputs Format

According to vLLM 0.11+ documentation:
- Uses `extra_body={"structured_outputs": {"json": schema}}`
- Returns JSON string in `message.content`
- No tool calls involved

### PydanticAI Format

- Uses `tools` + `tool_choice="required"`
- Expects JSON in `tool_calls[0].function.arguments`
- Validates against Pydantic model

### Conversion Flow

1. **Request Interception**: `VLLMChatWrapper.completions.create()` intercepts requests
2. **Detection**: Checks if `tool_choice="required"` and exactly one tool
3. **Conversion**: Extracts JSON schema → `extra_body.structured_outputs`
4. **Request**: Sends to vLLM with converted format
5. **Response**: Receives JSON in `content`
6. **Back-conversion**: Wraps JSON in tool call structure
7. **Return**: PydanticAI receives expected format

## References

- [vLLM Structured Outputs Docs](https://docs.vllm.ai/en/stable/features/structured_outputs/)
- [PydanticAI Documentation](https://ai.pydantic.dev/)

