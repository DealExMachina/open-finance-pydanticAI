# What PydanticAI Needs to Deliver Responses API Benefits

## Current Limitation

**GitHub Issue**: [#2663 - OpenAI Responses: `previous_response_id` support](https://github.com/pydantic/pydantic-ai/issues/2663)

PydanticAI's `OpenAIResponsesModel` exists but lacks critical state management features needed to realize Responses API benefits.

## Required Changes

### 1. Store Response IDs

**Complexity**: Low
**Effort**: ~1-2 hours

PydanticAI needs to capture and store response IDs from each API call:

```python
# Current PydanticAI behavior (simplified)
class Agent:
    async def run(self, prompt: str):
        response = await self.model.request(messages, ...)
        # Response ID is NOT captured
        return AgentResult(output=response.output)

# What's needed
class Agent:
    def __init__(self, ...):
        self._last_response_id: Optional[str] = None  # NEW
    
    async def run(self, prompt: str):
        response = await self.model.request(
            messages,
            previous_response_id=self._last_response_id  # NEW
        )
        self._last_response_id = response.id  # NEW: Store for next turn
        return AgentResult(output=response.output)
```

**Changes needed**:
- Add `_last_response_id` field to Agent state
- Extract response ID from API response
- Pass `previous_response_id` in subsequent requests

### 2. Pass `previous_response_id` Parameter

**Complexity**: Low
**Effort**: ~30 minutes

Update the OpenAI request builder to include the parameter:

```python
# In OpenAIResponsesModel.request()
def build_request_params(self, messages, previous_response_id=None):
    params = {
        "model": self.model_name,
        "input": messages,
        # ... other params ...
    }
    
    if previous_response_id:  # NEW
        params["previous_response_id"] = previous_response_id
    
    return params
```

### 3. Support `store` Parameter (Optional)

**Complexity**: Low
**Effort**: ~1 hour

Enable server-side conversation storage:

```python
# In OpenAIChatModelSettings or ModelSettings
class OpenAIResponsesModelSettings(BaseModel):
    store: bool = False  # NEW: Enable server-side storage
    # ... existing fields ...

# When making request
if settings.store:
    params["store"] = True
```

### 4. Handle Built-In Tool Responses (Advanced)

**Complexity**: Medium-High
**Effort**: ~4-8 hours

Support OpenAI's built-in tools (web search, code interpreter, etc.) that return in Responses API format:

```python
# Parse built-in tool results from response
if response.output.type == "code_interpreter_output":
    # Handle code interpreter results
    pass
elif response.output.type == "web_search_output":
    # Handle web search results
    pass
```

This is needed to properly round-trip responses with `previous_response_id`.

**Related**: [Issue #2870 - OpenAI Responses API fails with built-in tools and reasoning](https://github.com/pydantic/pydantic-ai/issues/2870)

## Total Implementation Effort

### For Core Functionality (Items 1-3)

**Complexity**: **Low-Medium**
**Total Effort**: **3-5 hours** for experienced contributor

Changes needed:
- Add response ID tracking (~1-2 hours)
- Update request builder (~30 min)
- Add `store` parameter support (~1 hour)
- Testing and validation (~1-2 hours)

**Code changed**: ~3-4 files in `pydantic_ai/models/openai.py` and `pydantic_ai/agent/`

### For Full Support (Items 1-4)

**Complexity**: **Medium**
**Total Effort**: **10-15 hours**

Includes:
- Core functionality (3-5 hours)
- Built-in tool support (4-8 hours)
- Comprehensive testing (2-3 hours)

## Is This Complicated?

**No, not complicated** - but requires PydanticAI maintainer involvement:

### Why It's NOT Complicated

1. **Clear pattern**: OpenAI SDK already does this, can copy approach
2. **Small surface area**: Only affects OpenAI models, not other providers
3. **Backward compatible**: Optional feature, existing code unaffected
4. **Well-defined**: OpenAI Responses API spec is clear

### Why It Requires PydanticAI Team

1. **Architecture decisions**: How to expose state management to users
2. **Multi-provider support**: How to handle Anthropic, Google, etc.
3. **API design**: User-facing API for conversation state
4. **Testing**: Need comprehensive test coverage

## Cost Assessment

### For PydanticAI Project

**Development Cost**: Low ($500-1500 if contracted)
- Core feature: 1-2 days of developer time
- Well-scoped, clear requirements
- Existing issue with user demand

**Maintenance Cost**: Minimal
- No breaking changes required
- Optional feature (opt-in)
- Follows OpenAI spec (stable)

### For Your Project

**DIY Cost**: High (not recommended)
- Fork PydanticAI: Maintenance burden
- Custom wrapper: Loses PydanticAI benefits
- Raw OpenAI SDK: Rewrite all agents

**Wait Cost**: Zero
- Continue with Chat Completions
- Re-evaluate when #2663 is resolved
- No technical debt

## Community Interest

Issue #2663 shows this is wanted by the community. The PydanticAI team will likely implement it, but timeline unknown.

### Alternative: Contribute to PydanticAI

If you want this feature:

1. **Comment on issue #2663** with your use case and test results
2. **Offer to contribute** if team provides guidance
3. **Reference**: Show your multi-turn test results demonstrating need

Your test data showing "0% cache hits without previous_response_id" is valuable evidence.

## Recommendation

**For Your Project**: 
- ❌ Don't fork/DIY - too costly
- ✅ Document limitation in your research
- ✅ Contribute findings to PydanticAI issue #2663
- ✅ Revisit in 3-6 months when feature may be implemented

**For PydanticAI Community**:
- Share your multi-turn test results on issue #2663
- Explain the 0% cache hit problem
- Offer to test once implemented

## Comparison: With vs Without previous_response_id

### Current Reality (Without)
```
Turn 1: 934 tokens → Server processes all
Turn 2: 465 tokens → Server processes all (no context reuse)
Turn 3: 533 tokens → Server processes all (no context reuse)
Total: 1,932 tokens billed
Cache hits: 0 tokens
```

### With previous_response_id (Expected)
```
Turn 1: 934 tokens → Server processes all
Turn 2: 465 tokens → Server caches ~300 tokens (context reuse)
         Billed: ~165 tokens
Turn 3: 533 tokens → Server caches ~400 tokens (cumulative context)
         Billed: ~133 tokens
Total: ~1,232 tokens billed (36% savings)
Cache hits: ~700 tokens
```

## PydanticAI Has `message_history` - But Not For Responses API

### Discovery: PydanticAI Already Has State Management!

PydanticAI supports conversation state via `message_history` parameter:

```python
# Session wrapper pattern (from PydanticAI docs)
class AgentSession:
    def __init__(self, agent):
        self.agent = agent
        self.history = []
    
    def run(self, query: str):
        result = self.agent.run_sync(query, message_history=self.history)
        self.history.extend(result.new_messages())  # Accumulate context
        return result.output
```

**This works for Chat Completions** - the message history is resent each turn.

### The Gap: Responses API Integration

The `message_history` mechanism exists but **doesn't leverage Responses API's `previous_response_id`**:

**Current behavior**:
- Chat API: ✅ Resends `message_history` each turn (works, but uses tokens)
- Responses API: ❌ Ignores `message_history`, doesn't pass `previous_response_id`

**What's needed**:
When using `OpenAIResponsesModel`, PydanticAI should:
1. Extract response ID from Responses API response
2. Pass `previous_response_id` instead of resending full `message_history`
3. Let the server handle context via cache

## Implementation Complexity Assessment

### Minimal Fix (Responses API Only)

**Complexity**: Low
**Effort**: 3-5 hours for core team
**Cost**: $300-750 if contracted

**Changes**:
1. Modify `OpenAIResponsesModel` to store last response ID
2. Pass `previous_response_id` when available
3. Add `store` parameter to settings
4. Update tests

**Files affected**: 2-3 files in `pydantic_ai/models/`

### Elegant Solution (Architecture Refactor)

**Complexity**: Medium
**Effort**: 1-2 days
**Cost**: $1,000-3,000 if contracted

**Changes**:
1. Add conversation state management abstraction
2. Support both message_history (Chat) and previous_response_id (Responses)
3. Handle built-in tool responses
4. Support multi-provider state patterns
5. Comprehensive testing

**Files affected**: 5-8 files across agent and models

## Why This Isn't Your Job

### Reasons NOT to DIY

1. **Maintenance burden**: Fork creates divergence from upstream
2. **Breaking changes**: Future PydanticAI updates may conflict
3. **Community benefit**: Your work wouldn't help others
4. **Time investment**: 10-20 hours total (design + impl + test)
5. **Uncertain ROI**: Even with caching, may not help your agents

### Better Approach

**Contribute to PydanticAI instead**:

1. **Document your findings** on issue #2663:
   - Share your multi-turn test results
   - Show 0% cache hit rate without `previous_response_id`
   - Demonstrate potential 20-40% savings with proper implementation

2. **Offer to test** when implemented:
   - You have comprehensive test suite ready
   - Real-world financial agent use case
   - Can validate cache performance

3. **Wait for implementation**:
   - Issue is already tracked
   - Feature has community interest
   - Let PydanticAI team design proper API

## What You CAN Do Today

### Workaround: Use message_history with Chat API

The `message_history` parameter already works for maintaining context:

```python
from pydantic_ai import Agent

agent = Agent(model, ...)
history = []

# Turn 1
result1 = await agent.run("Analyze portfolio...", message_history=history)
history.extend(result1.new_messages())

# Turn 2 (with context from Turn 1)
result2 = await agent.run("Adjust for risk...", message_history=history)
history.extend(result2.new_messages())

# Turn 3 (with context from Turn 1-2)
result3 = await agent.run("Tax optimization...", message_history=history)
```

**Benefits**:
- ✅ Works TODAY with Chat API
- ✅ Maintains full context
- ✅ No code changes needed
- ❌ Resends full history each turn (uses tokens)
- ❌ No cache hits (but functional)

## Expected Timeline for PydanticAI Support

**Optimistic**: 1-3 months
- Issue is clear and scoped
- Multiple users requesting
- Core team capable

**Realistic**: 3-6 months
- Depends on team priorities
- May wait for more user demand
- Need to design proper API

**Pessimistic**: 6-12 months or never
- Low priority vs other features
- Small user base for Responses API
- Team focused elsewhere

## Bottom Line

**Implementation is straightforward** (3-5 hours core work) but:
- Requires PydanticAI maintainer involvement
- Not your responsibility to fork/maintain
- Your test results can help prioritize the feature

**Your best action**:
1. Document findings in issue #2663
2. Continue with Chat API + message_history
3. Monitor issue for updates
4. Re-evaluate when feature ships

The research was valuable - you now have data proving:
- Responses API works technically ✅
- Enhanced token details available ✅
- PydanticAI lacks critical feature ❌
- Implementation is feasible but out of scope ✓

