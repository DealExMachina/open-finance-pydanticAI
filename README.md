# Open Finance PydanticAI

Research project evaluating small language models' (8B parameters) capability to call tools and produce structured outputs using PydanticAI.

## Objective

Evaluate whether 8B models can reliably:
- Call tools for financial calculations
- Generate structured outputs using Pydantic schemas
- Maintain accuracy with client-side verification

**Key Finding**: Small models (8B) are viable when tool calling is explicitly enforced, structured outputs are used, and client-side verification is performed.

## Agents

Five specialized agents demonstrate different capabilities:

### Agent 1: Portfolio Extractor
Extracts structured portfolio data from natural language. Parses positions (symbol, quantity, price) and calculates total value.

**File**: `examples/agent_1.py`

### Agent 2: Financial Calculator
Performs financial calculations using numpy-financial tools: future value, monthly payments, present value, interest rates, portfolio performance.

**Files**: 
- `examples/agent_2.py` - Main calculator
- `examples/agent_2_compliance.py` - Compliance wrapper with tool usage verification

### Agent 3: Multi-Step Workflow
Orchestrates specialized sub-agents for comprehensive analysis:
- Risk Analyst: Investment risk evaluation (1-5 scale)
- Tax Advisor: French tax implications (PEA, assurance-vie, compte-titres)
- Portfolio Optimizer: Asset allocation recommendations

**File**: `examples/agent_3.py`

### Agent 4: Option Pricing
Calculates option prices and Greeks (Delta, Gamma, Vega, Theta) using QuantLib.

**Files**:
- `examples/agent_4.py` - Main pricing agent
- `examples/agent_4_compliance.py` - Compliance wrapper

### Agent 5: SWIFT/ISO 20022 Processing
Three specialized variants:
- **Convert**: Bidirectional SWIFT MT103 ↔ ISO 20022 pacs.008 conversion
- **Validate**: Message structure, format, and field validation
- **Risk Assessment**: AML/KYC risk scoring for financial messages

**Files**:
- `examples/agent_5.py` - Conversion agent
- `examples/agent_5_validator.py` - Validation agent
- `examples/agent_5_risk.py` - Risk assessment agent

### Judge Agent
Critical evaluation agent using Llama 70B (via LLM Pro Finance) to assess all agent outputs. Reviews correctness, quality, tool usage, and provides improvement suggestions.

**File**: `examples/judge_agent.py`

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Configuration

Create `.env` file:

```env
ENDPOINT=koyeb
API_KEY=not-needed
MAX_TOKENS=1500

# Optional: Llama 70B for Judge Agent
LLM_PRO_FINANCE_KEY=your-api-key-here
LLM_PRO_FINANCE_URL=https://api.llm-pro-finance.com
```

### Start Gradio App

```bash
python app/gradio_app.py
```

The app will be available at `http://localhost:7860` with tabs for each agent.

### Usage

```python
from examples.agent_1 import agent_1, Portfolio
from examples.agent_2 import agent_2

# Structured extraction
result = await agent_1.run("Portfolio: 50 AIR.PA at 120€", output_type=Portfolio)

# Financial calculations
result = await agent_2.run("50000€ at 4% for 10 years. Future value?")
```

## Evaluation

Run comprehensive evaluation suite:

```bash
python examples/evaluate_all_agents.py
```

Results saved to `examples/evaluate_all_agents_results.json` with token usage, tool call verification, correctness validation, and inference speed.

## Model Deployment

Requires a running model instance. Deploy `DragonLLM/Qwen-Open-Finance-R-8B` on:
- **Koyeb** (recommended) - vLLM backend
- **Hugging Face Spaces** - TGI backend
- Any OpenAI-compatible API endpoint

See [simple-llm-pro-finance](https://github.com/DealExMachina/simple-llm-pro-finance) for deployment instructions.

**Model Specifications**:
- Model: `DragonLLM/Qwen-Open-Finance-R-8B`
- Context: 8192 tokens
- Tool Calling: Requires explicit vLLM configuration
- Language: French financial terminology optimized

## Best Practices

- Use `max_output_tokens` (600-1500) to stay within context limits
- Calculate totals client-side (model arithmetic unreliable)
- Use structured outputs (Pydantic) for validation
- Implement explicit tool calling instructions in prompts

## References

- Model: DragonLLM/Qwen-Open-Finance-R-8B - [arXiv:2511.08621](https://arxiv.org/abs/2511.08621)
- PydanticAI: [https://ai.pydantic.dev/](https://ai.pydantic.dev/)
- numpy-financial: [https://numpy.org/numpy-financial/](https://numpy.org/numpy-financial/)
- QuantLib: [https://www.quantlib.org/](https://www.quantlib.org/)
