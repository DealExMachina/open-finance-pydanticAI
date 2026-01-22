# Open Response Standard Implementation Plan

## Overview

This document outlines the implementation plan for consuming vLLM's **Open Response Standard** in the `open-finance-pydanticAI` project. The Open Response Standard provides enhanced token tracking and comprehensive streaming events that we can leverage for better observability and agent performance monitoring.

## What is the Open Response Standard?

The Open Response Standard is vLLM's enhanced OpenAI-compatible response protocol that includes:

### 1. Enhanced Token Tracking

**InputTokensDetails**:
- `cached_tokens` (int): Number of cached tokens
- `input_tokens_per_turn` (list[int]): Input tokens broken down per turn
- `cached_tokens_per_turn` (list[int]): Cached tokens broken down per turn

**OutputTokensDetails**:
- `reasoning_tokens` (int): Tokens used for reasoning
- `tool_output_tokens` (int): Tokens from tool outputs
- `output_tokens_per_turn` (list[int]): Output tokens broken down per turn
- `tool_output_tokens_per_turn` (list[int]): Tool output tokens broken down per turn

### 2. Streaming Response Events

Comprehensive event system for real-time streaming:
- `ResponseCreatedEvent` - Response lifecycle start
- `ResponseInProgressEvent` - Intermediate progress updates
- `ResponseCompletedEvent` - Response lifecycle end
- `ResponseContentPartAddedEvent` / `ResponseContentPartDoneEvent` - Content parts
- `ResponseReasoningTextDeltaEvent` / `ResponseReasoningTextDoneEvent` - Reasoning content
- Tool events (code interpreter, web search, MCP calls)

## Current State

- **Client Library**: OpenAI Python SDK (via PydanticAI)
- **Endpoints**: Koyeb, HuggingFace Spaces, Ollama, LLM Pro Finance
- **Observability**: Langfuse + Logfire integration
- **Token Tracking**: Basic token counts from `usage` field

## Implementation Tasks

### 1. Update Response Parsing

Enhance response handling to extract enhanced token details:
- [ ] Create utility functions to parse `InputTokensDetails` and `OutputTokensDetails`
- [ ] Update `app/models.py` or response handlers to extract enhanced metrics
- [ ] Handle both old and new response formats for backward compatibility

### 2. Enhanced Metrics Recording

Update observability integrations to use enhanced token data:
- [ ] Update `app/logfire_metrics.py` to record per-turn token breakdowns
- [ ] Update `app/langfuse_integration.py` to track reasoning tokens and tool output tokens
- [ ] Add metrics for cached tokens (cache hit rate tracking)

### 3. Streaming Event Handling

Implement streaming event processing:
- [ ] Create event handler for `ResponseCreatedEvent`, `ResponseCompletedEvent`
- [ ] Process `ResponseReasoningTextDeltaEvent` for reasoning model support
- [ ] Track tool events for better tool call observability
- [ ] Update Gradio UI to show streaming events in real-time

### 4. Agent Performance Analysis

Leverage enhanced metrics for better agent evaluation:
- [ ] Update `app/logfire_evaluation.py` to use per-turn token breakdowns
- [ ] Add cache efficiency metrics to evaluation scores
- [ ] Track reasoning token usage for reasoning models
- [ ] Enhance tool call analysis with tool output token tracking

### 5. Update Documentation

- [ ] Document new token tracking capabilities in README
- [ ] Add examples of enhanced response parsing
- [ ] Update observability documentation with new metrics

### 6. Testing

- [ ] Test with server that supports open response standard
- [ ] Verify backward compatibility with older response format
- [ ] Test streaming event handling
- [ ] Integration tests for enhanced metrics

## Code Changes Required

### Files to Modify

1. **`app/models.py`**:
   - Add response parsing for enhanced token details
   - Extract `InputTokensDetails` and `OutputTokensDetails` from responses

2. **`app/logfire_metrics.py`**:
   - Update `record_agent_run()` to accept enhanced token details
   - Add metrics for cached tokens, reasoning tokens, tool output tokens
   - Record per-turn token breakdowns

3. **`app/langfuse_integration.py`**:
   - Update trace recording to include enhanced token details
   - Track reasoning tokens separately
   - Record tool output tokens

4. **`app/gradio_app.py`** (optional):
   - Add UI elements to display enhanced token metrics
   - Show streaming events in real-time

5. **`app/logfire_evaluation.py`**:
   - Update scoring to use enhanced token metrics
   - Add cache efficiency scoring
   - Track reasoning token usage

## Example Implementation

```python
# app/models.py - Enhanced response parsing
from typing import Optional, Dict, Any

def extract_enhanced_token_details(response: Any) -> Dict[str, Any]:
    """Extract enhanced token details from vLLM open response standard."""
    usage = getattr(response, 'usage', None)
    if not usage:
        return {}
    
    details = {
        'input_tokens': getattr(usage, 'prompt_tokens', 0),
        'output_tokens': getattr(usage, 'completion_tokens', 0),
    }
    
    # Enhanced details if available
    if hasattr(usage, 'input_tokens_details'):
        input_details = usage.input_tokens_details
        details['cached_tokens'] = getattr(input_details, 'cached_tokens', 0)
        details['input_tokens_per_turn'] = getattr(input_details, 'input_tokens_per_turn', [])
        details['cached_tokens_per_turn'] = getattr(input_details, 'cached_tokens_per_turn', [])
    
    if hasattr(usage, 'output_tokens_details'):
        output_details = usage.output_tokens_details
        details['reasoning_tokens'] = getattr(output_details, 'reasoning_tokens', 0)
        details['tool_output_tokens'] = getattr(output_details, 'tool_output_tokens', 0)
        details['output_tokens_per_turn'] = getattr(output_details, 'output_tokens_per_turn', [])
        details['tool_output_tokens_per_turn'] = getattr(output_details, 'tool_output_tokens_per_turn', [])
    
    return details
```

## References

- [vLLM Open Response Protocol Docs](https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/responses/protocol/)
- [vLLM GitHub Repository](https://github.com/vllm-project/vllm)
- [Server Implementation](../simple-llm-pro-finance/docs/OPEN_RESPONSES_IMPLEMENTATION.md)

## Next Steps

1. Verify server supports open response standard
2. Test response format with sample requests
3. Implement response parsing utilities
4. Update observability integrations
5. Test with all agents and endpoints
