# vLLM Official Position on Responses API Storage

## GitHub Research Summary

### Key Issue: RFC #24603

**[RFC]: Responses API full functionality without stores**
- Link: https://github.com/vllm-project/vllm/issues/24603
- Status: Open proposal
- Date: Recent (2025-2026)

### The Problem

vLLM currently implements Responses API endpoint (`/v1/responses`) but:
- ✅ API endpoint works
- ✅ Returns response IDs
- ❌ Doesn't store responses
- ❌ `previous_response_id` lookup fails (404 error)

This confirms our test findings!

### The Proposal (RFC #24603)

**Goal**: Enable Responses API without requiring backend stores

**Approach**: Stateless conversation management
- Return messages in API response (not just response ID)
- Accept messages in subsequent requests
- Client maintains conversation state (not server)
- Enable load balancing across different servers

**Benefits**:
- No database required
- Stateless deployment (scales horizontally)
- Compatible with distributed/serverless architecture
- Client has full control over conversation state

**Trade-offs**:
- Client must manage state (more complexity)
- Full messages in each response (larger payloads)
- No server-side caching optimization

### Current vLLM Design Philosophy

**Stateless by design**:
- Optimized for throughput, not state management
- Each request is independent
- No database dependencies
- Scales horizontally without coordination

**Why no response storage**:
- vLLM is an **inference engine**, not a **conversation service**
- Adding storage would require database, state sync, etc.
- Goes against core design principle

---

## vLLM Prefix Caching (APC) - The Alternative

### What It Is

**Automatic Prefix Caching** (enabled via `--enable-prefix-caching`):
- Caches KV blocks for common prefixes
- Reuses computation when requests share prompt prefixes
- Hash-based block-level caching

### How It Works

```
Request 1: "System: You are an advisor\nUser: Analyze portfolio X"
           ^^^^^^^^^^^^^^^^^^^^^^^^ (cached as blocks)

Request 2: "System: You are an advisor\nUser: Adjust portfolio X"
           ^^^^^^^^^^^^^^^^^^^^^^^^ (cache hit!)
           Reuses cached KV blocks, only processes new tokens
```

### Benefits

- ✅ Reduces prefill time (prompt processing)
- ✅ Works across different requests
- ✅ Automatic (no client changes needed)
- ✅ Stateless (no conversation storage)

### Limitations

**Prefix-only matching**:
- Only reuses exact prefix matches
- Won't help with "continued" conversations where history grows
- Example that won't cache:
  ```
  Turn 1: "System + User Q1"          → Process all
  Turn 2: "System + User Q1 + A1 + User Q2"  → Can't reuse (different prefix)
  ```

**Current issues** (from GitHub):
- KV cache doesn't persist well across separate API requests
- Cache offloads to 0% after each request completes
- May work within batches but not across sequential calls

**Our servers**: Prefix caching NOT enabled
- Not in `start-vllm.sh` configuration
- Would need `--enable-prefix-caching` flag

---

## Two Different Caching Mechanisms

### 1. Responses API Caching (OpenAI Model)

**Mechanism**: Response storage with `previous_response_id`
```
Turn 1: Query → Response stored as resp_abc123
Turn 2: Query + previous_response_id=resp_abc123
        → Server loads stored response
        → Provides full conversation context
        → KV cache reused from Turn 1
```

**Requirements**:
- Database to store responses
- Response lookup by ID
- State management
- NOT implemented in vLLM

### 2. Prefix Caching (vLLM Feature)

**Mechanism**: Automatic KV cache reuse for shared prefixes
```
Request A: "System prompt + Context + Question A"
           ^^^^^^^^^^^^^^^^^^^^^ (cached)

Request B: "System prompt + Context + Question B"
           ^^^^^^^^^^^^^^^^^^^^^ (cache hit!)
           Only process "Question B"
```

**Requirements**:
- `--enable-prefix-caching` flag
- Identical prefixes across requests
- NOT enabled on your servers

**Limitation**: Doesn't help with growing conversation history
- Each turn adds to history → different prefix
- Can't reuse previous turn's cache

---

## vLLM's Position: RFC #24603 Approach

### Proposed Architecture

**Stateless Responses API**:
```python
# Turn 1
response1 = responses.create(input="Q1")
# Returns: {
#   "id": "resp_123",
#   "output": [...],
#   "messages": [system, user, assistant]  # Full context
# }

# Turn 2  
response2 = responses.create(
    input="Q2",
    previous_messages=response1.messages  # Client provides context
)
# Server processes full context, no storage needed
```

**Key difference from OpenAI**:
- OpenAI: Server stores response, `previous_response_id` → lookup
- vLLM (proposed): Client stores messages, provides in next request

**Benefits**:
- ✅ No database required
- ✅ Stateless deployment
- ✅ Load balancing friendly
- ❌ No cache optimization
- ❌ Client complexity

---

## What This Means for Your Project

### Current State

**Your vLLM deployment**:
- Responses API endpoint: ✅ Available
- Response storage: ❌ Not implemented
- Prefix caching: ❌ Not enabled
- Status: Stateless inference only

### Options to Enable Caching

#### Option A: Enable vLLM Prefix Caching

**Implementation**: Add to `start-vllm.sh`
```bash
VLLM_ARGS+=(--enable-prefix-caching)
```

**Benefits**:
- Automatic KV cache reuse for shared prefixes
- Works with Chat Completions API
- No client changes needed
- Stateless (no database)

**Limitations**:
- Only helps with identical prompt prefixes
- May not persist across API requests (known issue)
- Won't help with growing conversation history

**Effort**: 5 minutes (add flag, redeploy)
**Value**: Medium (depends on workload)

#### Option B: Wait for RFC #24603 Implementation

**Status**: Proposal stage, not implemented

**When implemented**:
- Stateless Responses API (client manages state)
- No server storage required
- No automatic caching benefits

**Timeline**: Unknown (6-12 months?)

**Value**: Low (no caching anyway)

#### Option C: Build Custom Response Storage

**Implementation**:
- Add Redis/database for response storage
- Proxy layer to handle lookups
- KV cache management

**Effort**: 2-4 weeks
**Maintenance**: Ongoing
**Value**: Not worth it

#### Option D: Use OpenAI

**Implementation**: Switch endpoint to OpenAI
**Benefit**: Full Responses API with caching
**Cost**: Pay for OpenAI tokens
**Value**: Only if caching saves >50% tokens

---

## Recommendation: Enable Prefix Caching

### Quick Win

Add `--enable-prefix-caching` to your vLLM deployment:

**File**: `simple-llm-pro-finance/start-vllm.sh`

```bash
# After line 51 (VLLM_ARGS array)
VLLM_ARGS+=(--enable-prefix-caching)
```

**Expected benefits**:
- System prompts cached across requests
- Repeated context (portfolio data) cached
- May provide 10-20% token savings for your use case
- Works with existing Chat Completions API

**Testing**:
- Redeploy to Koyeb/HF with flag
- Run same multi-turn scenarios
- Measure cache hits via `prompt_tokens_details.cached_tokens`

**Risk**: Low
- Flag is well-tested
- No breaking changes
- Can disable if issues arise

### Why This is Better Than Responses API

**Prefix caching** (with Chat Completions):
- ✅ Works with your existing code
- ✅ No client changes needed
- ✅ Stateless (no database)
- ✅ Automatic cache management
- ⚠️ Limited to exact prefix matches

**Responses API** (with storage):
- ❌ Requires database
- ❌ Requires custom proxy
- ❌ Complex state management
- ❌ Maintenance burden
- ✅ Flexible cache patterns

---

## vLLM Roadmap Insights

Based on GitHub research:

**Immediate (Current)**:
- Responses API endpoint: ✅ Implemented
- Response storage: ❌ Out of scope
- Prefix caching: ✅ Available (needs enabling)

**Near-term (RFC #24603)**:
- Stateless Responses API: 📋 Proposed
- Client-side state management: 📋 Proposed
- No server storage required: 📋 Goal

**Long-term**:
- Full OpenAI parity: ❓ Unlikely
- Response storage: ❓ Not planned
- vLLM philosophy: Stateless inference

### vLLM's Strategic Position

vLLM positions itself as:
- **Inference engine** (not conversation service)
- **Stateless by design** (horizontal scaling)
- **Performance-focused** (throughput over features)

Adding response storage would:
- Require database infrastructure
- Add state synchronization complexity
- Go against core design principles
- Become "yet another API service" (not their goal)

**Conclusion**: vLLM will likely never implement full OpenAI-style response storage. RFC #24603's stateless approach aligns with their philosophy.

---

## Actionable Recommendations

### For Your Project (Immediate)

1. **Enable prefix caching on vLLM** (5 min effort)
   - Edit `start-vllm.sh`
   - Add `--enable-prefix-caching`
   - Redeploy to Koyeb and HF
   - Test with existing agents

2. **Measure prefix cache effectiveness** (1 hour)
   - Run multi-turn scenarios
   - Check `cached_tokens` in Chat API responses
   - Compare with/without flag
   - Decision: Keep if >10% savings

3. **Archive Open Responses research** (Done)
   - Document findings
   - Keep test scripts for reference
   - Return to main branch

### For vLLM Community

1. **Monitor RFC #24603**
   - Stateless Responses API proposal
   - May enable better client-side state management
   - Timeline: 6-12 months

2. **Don't expect OpenAI parity**
   - vLLM won't implement response storage
   - Design philosophy is fundamentally different
   - Focus on what vLLM does well (inference)

---

## Comparison Matrix

| Feature | OpenAI | vLLM (Current) | vLLM (RFC #24603) | Your Need |
|---------|--------|----------------|-------------------|-----------|
| Responses endpoint | ✅ | ✅ | ✅ | ✓ |
| Response storage | ✅ | ❌ | ❌ | ✗ (not critical) |
| Cache via previous_response_id | ✅ | ❌ | ❌ | ✗ (nice-to-have) |
| Prefix caching | ✅ | ✅* | ✅* | ✓ (enable it!) |
| Stateless deployment | ❌ | ✅ | ✅ | ✓ (required) |
| Client state management | ❌ | ✅ | ✅ | ✓ (already doing) |

*Requires `--enable-prefix-caching` flag

---

## Bottom Line

**vLLM's approach is different, not inferior**:
- OpenAI: Stateful service with storage (caching via response IDs)
- vLLM: Stateless engine with prefix caching (caching via prompt matching)

**For your self-hosted deployment**:
1. ✅ Enable prefix caching (quick win)
2. ✅ Use Chat Completions API
3. ✅ Use `message_history` for multi-turn
4. ❌ Don't pursue Responses API caching (incompatible architecture)

**Next action**: Test prefix caching on your vLLM servers to see if it provides 10-20% token savings for your workload.
