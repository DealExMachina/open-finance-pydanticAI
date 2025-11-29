# Open Finance PydanticAI

Research project studying tool calling and structured outputs with small language models (8B parameters).

**Note**: Simplified examples for research purposes, not production-ready.

## Research Objective

Investigates whether 8B models can reliably:
1. Trigger tools for financial calculations
2. Generate structured outputs using Pydantic schemas

**Key Finding**: Small models (8B) are viable when tool calling is explicitly enforced, structured outputs are used, and client-side verification is performed.

## Overview

Financial AI agents using PydanticAI with `DragonLLM/Qwen-Open-Finance-R-8B` (8B parameters, French financial terminology). Uses numpy-financial and QuantLib for calculations.

## Agents

1. **Agent 1** - Structured data extraction (portfolio positions)
2. **Agent 2** - Financial calculations (numpy-financial)
3. **Agent 3** - Multi-step workflows (risk, tax, optimization)
4. **Agent 4** - Option pricing (QuantLib)
5. **Agent 5** - SWIFT MT ↔ ISO 20022 conversion, validation, risk assessment

## Installation

```bash
pip install -e ".[dev]"
```

Create `.env`:
```env
ENDPOINT=koyeb
API_KEY=not-needed
MAX_TOKENS=1500
```

## Usage

```python
from examples.agent_1 import agent_1, Portfolio
from examples.agent_2 import agent_2
from examples.agent_5 import agent_5

# Structured extraction
result = await agent_1.run("Portfolio: 50 AIR.PA at 120€", output_type=Portfolio)

# Financial calculations
result = await agent_2.run("50000€ at 4% for 10 years. Future value?")

# SWIFT conversion
result = await agent_5.run("Convert SWIFT MT103 to ISO 20022: ...")
```

## Testing

```bash
# Quick evaluation
python examples/evaluate_all_agents.py

# Agent 5 synthetic test suite (10 cases)
python examples/test_agent_5_synthetic.py
```

Results saved to JSON:
- `examples/evaluate_all_agents_results.json` - Full agent outputs
- `examples/test_agent_5_results.json` - Agent 5 detailed results

## Performance

**Synthetic Test Suite (10 cases per agent):**
- Total: 50 tests, 100% success rate
- Tool calling: 100% success
- Structured outputs: 100% validation

| Agent | Avg Tokens | Avg Time (s) |
|-------|------------|--------------|
| Agent 1 | 707 | 4.49 |
| Agent 2 | 4,121 | 15.29 |
| Agent 3 | 3,132 | 16.90 |
| Agent 4 | 3,053 | 22.50 |
| Agent 5 | 9,195 | 79.11 |

## Model

- **Model**: `DragonLLM/Qwen-Open-Finance-R-8B`
- **Context**: 8192 tokens (requires careful management)
- **Deployment**: Koyeb (vLLM) or Hugging Face Space (TGI)
- **Tool Calling**: Requires explicit configuration for vLLM

## Best Practices

- Use `max_output_tokens` (600-1500) to stay within context limits
- Calculate totals client-side (model arithmetic unreliable)
- Use structured outputs (Pydantic) for validation
- Implement explicit tool calling instructions in prompts

## Documentation

- `docs/model_capabilities_8b.md` - Model capabilities
- `docs/qwen3_specifications.md` - Model specifications
- `docs/swift_iso20022_tools_evaluation.md` - SWIFT/ISO 20022 tools

## References

- **Model**: DragonLLM/Qwen-Open-Finance-R-8B - [arXiv:2511.08621](https://arxiv.org/abs/2511.08621)
- **PydanticAI**: [https://ai.pydantic.dev/](https://ai.pydantic.dev/)
- **numpy-financial**: [https://numpy.org/numpy-financial/](https://numpy.org/numpy-financial/)
- **QuantLib**: [https://www.quantlib.org/](https://www.quantlib.org/)
