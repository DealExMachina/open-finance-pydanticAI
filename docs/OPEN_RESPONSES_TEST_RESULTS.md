# Open Responses API - Multi-Turn Test Results

## Test Date
January 22, 2026

## Executive Summary

Tested Responses API vs Chat Completions API in multi-turn financial scenarios to evaluate benefits of the Open Response Standard.

**VERDICT: ❌ No clear benefits for current implementation**

### Key Findings

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| Cache hit rate | > 30% | 0% | ❌ FAILED |
| Token reduction | > 15% | 13.2% | ❌ FAILED |
| Latency | < +20% overhead | -15.5% (faster!) | ✅ PASSED |

**Recommendation**: Keep Chat Completions as default API. Responses API provides marginal benefits not worth the complexity.

## Test Configuration

- **Endpoint**: Ollama (local)
- **Model**: qwen2.5:3b-instruct
- **PydanticAI Version**: 1.44.0
- **Scenarios Tested**: Portfolio Optimization, Calculator Chain (partial)

## Detailed Results

### Scenario 1: Portfolio Optimization Chain (4 turns)

**Chat Completions API:**
- Total tokens: 2,233
- Total latency: 53.67s
- Turn 1: 968 tokens (23.86s)
- Turn 2: 348 tokens (7.98s)
- Turn 3: 660 tokens (16.00s)
- Turn 4: 257 tokens (5.82s)

**Responses API:**
- Total tokens: 1,938
- Total latency: 45.37s (15.5% FASTER)
- Cached tokens: 0 (0% cache hit rate)
- Turn 1: 701 tokens (16.38s)
- Turn 2: 405 tokens (9.49s)
- Turn 3: 560 tokens (13.29s)
- Turn 4: 272 tokens (6.20s)

**Analysis:**
- Token reduction: 295 tokens (13.2%) - below 15% target
- Latency improvement: 8.3s faster (15.5% reduction) - unexpected benefit!
- Cache hits: ZERO - critical failure
- Token details available: ✅ `input_tokens_details`, `output_tokens_details`

### Scenario 2: Calculator Chain (with tools)

**Status**: Failed on Turn 1 with error
**Error**: `invalid message content type: <nil>` (400 Bad Request)
**Cause**: Ollama compatibility issue with PydanticAI tools in Chat API

**Note**: Could not compare tool_output_tokens tracking due to failure.

## Why No Cache Hits?

The 0% cache hit rate is due to **PydanticAI architecture limitation**:

### Root Cause: Missing `previous_response_id` Support

**GitHub Issue**: [#2663 - OpenAI Responses: `previous_response_id` support](https://github.com/pydantic/pydantic-ai/issues/2663)
- Status: Open (filed August 25, 2025)
- Problem: PydanticAI doesn't send `previous_response_id` parameter
- Impact: Each `agent.run()` treated as new conversation
- Result: 0% cache hit rate, no state reuse

### How Responses API Caching Works

```python
# Turn 1: Initial request
response1 = client.responses.create(
    model="model-name",
    input="Analyze this portfolio..."
)
# Returns: response1.id = "resp_abc123"

# Turn 2: Reference previous response
response2 = client.responses.create(
    model="model-name",
    input="Adjust for conservative risk...",
    previous_response_id="resp_abc123"  # <-- THIS IS MISSING IN PYDANTICAI
)
# Server loads cached context from response1
# Cache hit = reduced input tokens
```

### PydanticAI Current Behavior

```python
# Turn 1
result1 = await agent.run("Analyze portfolio...")
# Context: Built internally

# Turn 2
result2 = await agent.run("Adjust for risk...")
# Context: Turn 1 response NOT referenced
# Previous response ID: NOT passed to API
# Result: No cache hits
```

### Test Confirmation

Even with:
- Same agent instance (not recreated per turn)
- Contextual questions referencing prior turns
- Stateful conversation pattern

We still get 0% cache hits because PydanticAI doesn't link turns via `previous_response_id`.

## Enhanced Token Details Confirmed

Responses API DOES return structured token details:

```json
{
    "input_tokens_details": {
        "cached_tokens": 0,
        "input_tokens_per_turn": [],
        "cached_tokens_per_turn": []
    },
    "output_tokens_details": {
        "reasoning_tokens": 0,
        "tool_output_tokens": 0,
        "output_tokens_per_turn": [],
        "tool_output_tokens_per_turn": []
    }
}
```

**Value**: Enhanced observability for per-turn breakdown and reasoning/tool token separation.

## Unexpected Finding: Latency Improvement

Responses API was 15.5% FASTER than Chat Completions:
- Chat API: 53.67s total
- Responses API: 45.37s total
- Improvement: 8.3s (15.5% reduction)

This contradicts OpenAI reports of Responses API being slower. Possible explanations:
- Ollama implementation differs from OpenAI
- vLLM may have better Responses API performance
- Local inference has different characteristics

## Endpoint Availability Test Results

| Endpoint | Chat API | Responses API | Enhanced Token Details |
|----------|----------|---------------|------------------------|
| Koyeb vLLM | ✅ Works | ✅ Works | ✅ Full support |
| HF vLLM | ⚠️ Sleeping | ❓ Not tested | ❓ Unknown |
| Ollama | ✅ Works | ✅ Works | ✅ Full support |
| LLM Pro Finance | ✅ Works | ❓ Not tested | ❓ Unknown |

**Confirmed**: Both Koyeb vLLM and Ollama support Responses API with full `InputTokensDetails` and `OutputTokensDetails`.

## Recommendations

### Immediate Action: Do NOT proceed with full implementation

**Reasons**:
1. **No cache benefits**: 0% cache hit rate means no token savings
2. **Below target**: 13.2% token reduction insufficient
3. **Complexity not justified**: Implementation effort exceeds marginal benefits
4. **Single-turn agents**: Current agents don't benefit from stateful conversations

### What Would Make Responses API Worth It?

Responses API would provide value if:

1. **Stateful conversation management**
   - Maintain conversation state across turns
   - Pass `previous_response_id` between agent runs
   - Requires architectural change in how agents are invoked

2. **Genuinely multi-turn workflows**
   - Investment advisor with iterative refinement
   - Compliance workflows with progressive analysis
   - Not current single-question-answer pattern

3. **Cache hit rate > 30%**
   - Requires proper state management
   - May need server-side configuration
   - Unclear if achievable with current infrastructure

### Alternative: Enhanced Observability Only

**Minimal value path**: Use Responses API solely for enhanced token tracking:
- Per-turn token breakdowns for evaluation
- Reasoning token separation (if using reasoning models)
- Tool output token tracking

**Effort**: Already implemented in `app/models.py` (1 line parameter change)
**Value**: Marginal - current token tracking is sufficient

## Conclusion

**Decision**: Keep Chat Completions API as the default and only API type.

**Rationale**:
- Responses API provides no meaningful token reduction without cache hits
- Cache hits require stateful conversation management not in scope
- Current agents are single-turn, don't benefit from Responses API features
- 13.2% token reduction doesn't justify implementation complexity
- Enhanced token details nice-to-have, not critical

**Next Steps**:
1. Document these findings
2. Archive `impl/open-responses` branch with research
3. Focus on improving Chat Completions observability
4. Revisit Responses API when building genuinely multi-turn agentic workflows

## Test Commands Reference

```bash
# Test endpoint availability
curl -X POST "http://localhost:11434/v1/responses" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:3b-instruct","input":"test"}'

# Run multi-turn scenarios
python examples/test_multiturn_scenarios.py --endpoint ollama --scenario portfolio
python examples/test_multiturn_scenarios.py --endpoint koyeb --scenario all

# Check token details
python examples/test_responses_api.py
```

## Lessons Learned

1. **Test before implementing**: Multi-turn testing revealed cache hits don't work as expected
2. **Context matters**: Responses API benefits require proper state management
3. **Latency surprise**: Responses API was faster (15.5%), not slower
4. **Tool compatibility**: Some edge cases with tool calling in Chat API
5. **Don't assume benefits**: "40-80% savings" marketing doesn't apply to simple workflows
