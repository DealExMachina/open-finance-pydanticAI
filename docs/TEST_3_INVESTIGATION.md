# Test 3 Failure Investigation

## Problem

Test 3 (three positions) shows partial success:
- ✅ All 3 positions extracted correctly
- ❌ Total calculation is wrong: 2650€ or 3825€ instead of 4325€

## Expected Calculation

```
AIR.PA: 15 × 110€ = 1,650€
SAN.PA: 25 × 85€  = 2,125€
TTE.PA: 10 × 55€  =   550€
─────────────────────────
Total:             4,325€
```

## Actual Results

| max_tokens | Model Total | Calculated | Error | Notes |
|------------|-------------|------------|-------|-------|
| 800 | 2,650€ | 4,325€ | -1,675€ | Truncated (finish_reason: length) |
| 1200 | 3,000€ | 4,325€ | -1,325€ | Still wrong calculation |
| 2000 | 3,825€ | 4,325€ | -500€ | Closer, but still wrong |

## Root Cause

**Model arithmetic limitation**: The 8B reasoning model makes calculation errors, especially with multi-step arithmetic.

### Analysis

The model's reasoning shows it **knows** the correct calculation:
```
"Airbus: 15 * 110 = 1650, Sanofi: 25 * 85 = 2125, Total: 10 * 55 = 550. 
Adding those gives 1650 + 2125 = 3775, plus 550 is 4325."
```

But the actual JSON output has wrong totals:
- 3,825€ = 1,650 + 2,125 + 50 (TTE.PA calculated as 10×5 instead of 10×55)
- Or: 3,825€ = 1,650 + 2,125 + 1,050 (some other error)

### Additional Issues

1. **Reasoning text consumes tokens**: Even with `structured_outputs`, the model outputs `<think>` tags, consuming 40-60% of tokens
2. **Token limit truncation**: With `max_tokens=800`, responses get cut off mid-JSON
3. **Arithmetic errors**: The model makes mistakes in multi-step calculations

## Solutions

### Option 1: Increase max_tokens (Partial Fix)
- Increase `max_output_tokens` to 2000+ for reasoning models
- Still doesn't fix calculation errors
- **Status**: Tested, still has errors

### Option 2: Post-process and Recalculate (Recommended)
Add validation that recalculates totals from positions:

```python
# After getting result from model
portfolio = result.output
calculated_total = sum(p.quantite * p.prix for p in portfolio.positions)
if abs(portfolio.total - calculated_total) > 1:
    # Model made calculation error, use calculated value
    portfolio.total = calculated_total
```

### Option 3: Use Tool Calling for Calculations
Instead of relying on model to calculate, use a tool:

```python
@tool
def calculate_portfolio_total(positions: List[Position]) -> float:
    """Calculate total portfolio value."""
    return sum(p.quantite * p.prix for p in positions)
```

### Option 4: Accept as Model Limitation
- Document that 8B models have arithmetic limitations
- Use larger models (30B+) for accurate calculations
- Or always validate/recalculate totals

## Recommendation

**Implement Option 2** (post-processing validation):
- Fast and reliable
- Works with any model size
- Maintains compatibility with PydanticAI
- No changes to prompts needed

## Test Results Summary

| Test | Positions | Total Match | Status |
|------|-----------|-------------|--------|
| Test 1 (1 position) | ✅ | ✅ | Complete success |
| Test 2 (2 positions) | ✅ | ✅ | Complete success |
| Test 3 (3 positions) | ✅ | ❌ | Partial (calculation error) |

**Conclusion**: The extraction works perfectly. The failure is purely arithmetic - a known limitation of 8B reasoning models.

