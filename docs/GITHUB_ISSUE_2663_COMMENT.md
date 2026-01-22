# Comment for PydanticAI Issue #2663

## Test Results: 0% Cache Hits with Responses API + message_history

I've tested `OpenAIResponsesModel` with multi-turn conversations using `message_history` and can confirm **0% cache hits** across all turns, even though the Responses API returns cache tracking fields.

### Environment

- **PydanticAI Version**: 1.44.0
- **Tested with**: Ollama (qwen2.5:3b-instruct) and vLLM
- **API Type**: OpenAI Responses API (`/v1/responses`)

### Test Results

Running a 3-turn conversation with `message_history`:

```
Chat API:      1,794 total tokens, 0 cached (0%)
Responses API: 1,374 total tokens, 0 cached (0%)
```

**Expected**: Turn 2-3 should show 30-50% cache hits (via `previous_response_id`)
**Actual**: 0% cache hits on all turns

### Minimal Reproduction

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

async def test():
    # Setup (works with Ollama or OpenAI)
    model = OpenAIResponsesModel(
        model_name="qwen2.5:3b-instruct",
        provider=OpenAIProvider(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
    )
    agent = Agent(model, system_prompt="Be concise.")
    message_history = []
    
    # Turn 1
    result1 = await agent.run("Tell me about compound interest.", message_history=message_history)
    message_history.extend(result1.new_messages())
    print(f"Turn 1: {result1.usage().total_tokens} tokens, {result1.usage().cache_read_tokens} cached")
    
    # Turn 2 (references "it" from Turn 1)
    result2 = await agent.run("Can you explain it with an example?", message_history=message_history)
    message_history.extend(result2.new_messages())
    print(f"Turn 2: {result2.usage().total_tokens} tokens, {result2.usage().cache_read_tokens} cached")
    
    # Turn 3 (references "example" from Turn 2)
    result3 = await agent.run("What's the formula for that example?", message_history=message_history)
    print(f"Turn 3: {result3.usage().total_tokens} tokens, {result3.usage().cache_read_tokens} cached")
    
    # Expected: Turn 2-3 should have cached tokens > 0
    # Actual: All turns show 0 cached tokens

asyncio.run(test())
```

**Output**:
```
Turn 1: 144 tokens, 0 cached  ✓ Expected (first turn)
Turn 2: 422 tokens, 0 cached  ✗ Should have cache hits
Turn 3: 808 tokens, 0 cached  ✗ Should have cache hits
```

### Root Cause

The Responses API supports `previous_response_id` to reference prior responses and enable caching:

```python
# What OpenAI SDK does:
response1 = client.responses.create(model="...", input="...")
# Returns: response1.id = "resp_abc123"

response2 = client.responses.create(
    model="...",
    input="...",
    previous_response_id=response1.id  # <-- Enables caching
)
# Server loads cached context, reduces tokens
```

**PydanticAI doesn't pass `previous_response_id`**, so each turn is treated as a new conversation with no cache reuse.

### Impact

Without `previous_response_id` support, Responses API offers **no caching benefits**:

- Expected savings: 20-40% token reduction on Turn 2+ (via cache hits)
- Actual savings: 0% (no cache hits)
- Result: Responses API may use MORE tokens than Chat API

### What's Needed

PydanticAI should:

1. **Store response ID** after each Responses API call
2. **Pass `previous_response_id`** in subsequent requests when using `message_history`
3. **Support `store` parameter** for server-side conversation storage

Example implementation:

```python
class Agent:
    def __init__(self, ...):
        self._last_response_id: Optional[str] = None
    
    async def run(self, prompt, message_history=None, ...):
        # Build request with previous_response_id if available
        response = await self.model.request(
            messages,
            previous_response_id=self._last_response_id,  # NEW
            ...
        )
        
        # Store for next turn
        if hasattr(response, 'id'):
            self._last_response_id = response.id  # NEW
        
        return result
```

### Business Impact

For production multi-turn agents (customer support, financial advisors, etc.), proper caching could reduce:
- **Token costs**: 20-40% on Turn 2+
- **Latency**: Cached context loads faster
- **Infrastructure load**: Less processing on repeated context

Without this feature, Responses API provides no advantage over Chat Completions.

### Tested Endpoints

Confirmed Responses API works with enhanced token details on:
- ✅ vLLM (Koyeb deployment)
- ✅ Ollama (local)
- ✅ Returns `input_tokens_details` and `output_tokens_details`

But 0% cache hits across all endpoints due to missing `previous_response_id`.

### Files

Full test suite available if helpful:
- Minimal reproduction: `test_issue_2663.py` (above)
- Multi-turn scenarios: Portfolio optimization, financial calculations, etc.
- Comparison data: Chat vs Responses across multiple workflows

---

Happy to provide more details or test once this feature is implemented!
