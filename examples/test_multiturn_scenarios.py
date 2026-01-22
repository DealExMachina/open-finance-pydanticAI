#!/usr/bin/env python3
"""
Multi-turn scenario testing to prove Responses API benefits.

This script compares Chat Completions vs Responses API across multi-turn
financial workflows where context reuse and cache hits provide value.

Success criteria:
- Cache hit rate > 30% on Turn 2+
- Token reduction > 15% on Turn 2+
- Latency overhead < +20%

Usage:
    python examples/test_multiturn_scenarios.py --endpoint koyeb --scenario portfolio
    python examples/test_multiturn_scenarios.py --endpoint ollama --scenario all
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import get_model_for_endpoint
from app.config import settings
from pydantic_ai import Agent


@dataclass
class TurnResult:
    """Results from a single turn."""
    turn_num: int
    prompt: str
    api_type: str
    response: str
    elapsed_seconds: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    tool_output_tokens: int = 0
    input_tokens_per_turn: List[int] = None
    output_tokens_per_turn: List[int] = None


@dataclass
class ScenarioResult:
    """Results from a complete multi-turn scenario."""
    scenario_name: str
    api_type: str
    endpoint: str
    turns: List[TurnResult]
    
    @property
    def total_tokens(self) -> int:
        return sum(t.total_tokens for t in self.turns)
    
    @property
    def total_cached_tokens(self) -> int:
        return sum(t.cached_tokens for t in self.turns)
    
    @property
    def total_latency(self) -> float:
        return sum(t.elapsed_seconds for t in self.turns)
    
    @property
    def cache_hit_rate(self) -> float:
        """Percentage of tokens that were cache hits."""
        if self.total_tokens == 0:
            return 0.0
        return (self.total_cached_tokens / self.total_tokens) * 100


async def run_turn(agent, prompt: str, turn_num: int, api_type: str) -> TurnResult:
    """Run a single turn and extract metrics."""
    start = time.time()
    result = await agent.run(prompt)
    elapsed = time.time() - start
    
    # Extract usage
    usage = result.usage()
    
    # Extract output
    output_text = str(result.output) if hasattr(result, 'output') else str(result)
    
    # Build turn result
    turn_data = TurnResult(
        turn_num=turn_num,
        prompt=prompt[:100],
        api_type=api_type,
        response=output_text[:200],
        elapsed_seconds=elapsed,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        cached_tokens=usage.cache_read_tokens,
    )
    
    # Extract enhanced details if available (Responses API)
    if hasattr(usage, 'details') and usage.details:
        turn_data.reasoning_tokens = usage.details.get('reasoning_tokens', 0)
        turn_data.tool_output_tokens = usage.details.get('tool_output_tokens', 0)
        
        # Check for structured details
        if 'input_tokens_details' in usage.details:
            input_details = usage.details.get('input_tokens_details', {})
            if isinstance(input_details, dict):
                turn_data.cached_tokens = input_details.get('cached_tokens', 0)
                turn_data.input_tokens_per_turn = input_details.get('input_tokens_per_turn', [])
        
        if 'output_tokens_details' in usage.details:
            output_details = usage.details.get('output_tokens_details', {})
            if isinstance(output_details, dict):
                turn_data.reasoning_tokens = output_details.get('reasoning_tokens', 0)
                turn_data.tool_output_tokens = output_details.get('tool_output_tokens', 0)
                turn_data.output_tokens_per_turn = output_details.get('output_tokens_per_turn', [])
    
    return turn_data


# =============================================================================
# SCENARIO 1: Portfolio Optimization Chain
# =============================================================================

async def scenario_portfolio_optimization(endpoint: str, api_type: str) -> ScenarioResult:
    """Multi-turn portfolio optimization - benefits: state management, cache hits."""
    print(f"\n{'='*60}")
    print(f"SCENARIO 1: Portfolio Optimization Chain")
    print(f"API: {api_type.upper()} | Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    model = get_model_for_endpoint(endpoint, api_type)
    agent = Agent(model, system_prompt="You are a financial advisor specializing in portfolio optimization.")
    
    turns = []
    
    # Turn 1: Initial analysis
    print("\n[Turn 1] Initial portfolio analysis...")
    prompt1 = "Analyze this portfolio: 50% stocks (CAC40), 30% bonds (government), 20% real estate (SCPI). Total: 100000€, investment horizon 30 years, age 35."
    turn1 = await run_turn(agent, prompt1, 1, api_type)
    turns.append(turn1)
    print(f"  Tokens: {turn1.total_tokens} (in: {turn1.input_tokens}, out: {turn1.output_tokens}, cached: {turn1.cached_tokens})")
    print(f"  Latency: {turn1.elapsed_seconds:.2f}s")
    
    # Turn 2: Refine for risk (should cache Turn 1 portfolio context)
    print("\n[Turn 2] Adjust for conservative risk...")
    prompt2 = "The portfolio you just analyzed - adjust the allocation for a conservative risk profile. I'm risk-averse."
    turn2 = await run_turn(agent, prompt2, 2, api_type)
    turns.append(turn2)
    print(f"  Tokens: {turn2.total_tokens} (in: {turn2.input_tokens}, out: {turn2.output_tokens}, cached: {turn2.cached_tokens})")
    print(f"  Latency: {turn2.elapsed_seconds:.2f}s")
    if turn2.cached_tokens > 0:
        print(f"  ✅ Cache hit: {turn2.cached_tokens} tokens!")
    
    # Turn 3: Tax optimization (should cache Turn 1-2 context)
    print("\n[Turn 3] Tax optimization...")
    prompt3 = "For this adjusted portfolio, optimize for French tax efficiency. Consider PEA limits (150k€) and assurance-vie advantages."
    turn3 = await run_turn(agent, prompt3, 3, api_type)
    turns.append(turn3)
    print(f"  Tokens: {turn3.total_tokens} (in: {turn3.input_tokens}, out: {turn3.output_tokens}, cached: {turn3.cached_tokens})")
    print(f"  Latency: {turn3.elapsed_seconds:.2f}s")
    if turn3.cached_tokens > 0:
        print(f"  ✅ Cache hit: {turn3.cached_tokens} tokens!")
    
    # Turn 4: Final recommendation (should cache all prior context)
    print("\n[Turn 4] Final recommendation...")
    prompt4 = "Provide the final recommended allocation with rationale based on our discussion."
    turn4 = await run_turn(agent, prompt4, 4, api_type)
    turns.append(turn4)
    print(f"  Tokens: {turn4.total_tokens} (in: {turn4.input_tokens}, out: {turn4.output_tokens}, cached: {turn4.cached_tokens})")
    print(f"  Latency: {turn4.elapsed_seconds:.2f}s")
    if turn4.cached_tokens > 0:
        print(f"  ✅ Cache hit: {turn4.cached_tokens} tokens!")
    
    return ScenarioResult(
        scenario_name="portfolio_optimization",
        api_type=api_type,
        endpoint=endpoint,
        turns=turns,
    )


# =============================================================================
# SCENARIO 2: Financial Calculator Chain
# =============================================================================

async def scenario_calculator_chain(endpoint: str, api_type: str) -> ScenarioResult:
    """Multi-turn calculation workflow - benefits: tool output tokens tracking."""
    print(f"\n{'='*60}")
    print(f"SCENARIO 2: Financial Calculator Chain")
    print(f"API: {api_type.upper()} | Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    from examples.agent_2 import FinancialCalculationResult
    
    model = get_model_for_endpoint(endpoint, api_type)
    
    # Import tools from agent_2
    from examples.agent_2 import calculer_valeur_future, calculer_taux_interet, calculer_versement_mensuel
    
    agent = Agent(
        model,
        system_prompt="Financial calculator. Use tools for calculations.",
        tools=[calculer_valeur_future, calculer_taux_interet, calculer_versement_mensuel],
        output_type=FinancialCalculationResult,
    )
    
    turns = []
    
    # Turn 1: Calculate FV
    print("\n[Turn 1] Calculate future value...")
    prompt1 = "I have 50000€ to invest at 4% annual rate for 10 years. What will be the future value?"
    turn1 = await run_turn(agent, prompt1, 1, api_type)
    turns.append(turn1)
    print(f"  Tokens: {turn1.total_tokens} (tool_output: {turn1.tool_output_tokens})")
    
    # Turn 2: Calculate required rate (uses Turn 1 result)
    print("\n[Turn 2] Calculate required rate...")
    prompt2 = "If I want to double that future value in half the time (5 years), what rate would I need?"
    turn2 = await run_turn(agent, prompt2, 2, api_type)
    turns.append(turn2)
    print(f"  Tokens: {turn2.total_tokens} (cached: {turn2.cached_tokens}, tool_output: {turn2.tool_output_tokens})")
    
    # Turn 3: Loan comparison (uses both rates from Turn 1-2)
    print("\n[Turn 3] Compare loan payments...")
    prompt3 = "Compare monthly payments for borrowing 50000€ over 10 years at both the 4% rate and the higher rate you just calculated."
    turn3 = await run_turn(agent, prompt3, 3, api_type)
    turns.append(turn3)
    print(f"  Tokens: {turn3.total_tokens} (cached: {turn3.cached_tokens}, tool_output: {turn3.tool_output_tokens})")
    
    return ScenarioResult(
        scenario_name="calculator_chain",
        api_type=api_type,
        endpoint=endpoint,
        turns=turns,
    )


# =============================================================================
# SCENARIO 3: SWIFT Message Analysis Series
# =============================================================================

async def scenario_swift_analysis(endpoint: str, api_type: str) -> ScenarioResult:
    """Multi-turn SWIFT analysis - benefits: context reuse, reasoning tokens."""
    print(f"\n{'='*60}")
    print(f"SCENARIO 3: SWIFT Message Analysis Series")
    print(f"API: {api_type.upper()} | Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    model = get_model_for_endpoint(endpoint, api_type)
    agent = Agent(model, system_prompt="You are a SWIFT/ISO 20022 expert and compliance officer.")
    
    swift_message = """{1:F01BANKFRPPAXXX1234567890}
{2:O1031201234567BANKFRPPAXXX12345678901234N}
{4:
:20:REF123
:32A:240124EUR1000,00
:50K:/FR1420041010050500013M02606
COMPAGNIE ABC
123 RUE DE PARIS
75001 PARIS
:59:/DE89370400440532013000
COMPAGNIE XYZ
BERLIN
:71A:OUR
-}"""
    
    turns = []
    
    # Turn 1: Parse and validate
    print("\n[Turn 1] Parse SWIFT message...")
    prompt1 = f"Parse and validate this SWIFT MT103 message:\n{swift_message}"
    turn1 = await run_turn(agent, prompt1, 1, api_type)
    turns.append(turn1)
    print(f"  Tokens: {turn1.total_tokens}")
    
    # Turn 2: Convert to ISO 20022 (should cache SWIFT message)
    print("\n[Turn 2] Convert to ISO 20022...")
    prompt2 = "Convert this SWIFT message to ISO 20022 format."
    turn2 = await run_turn(agent, prompt2, 2, api_type)
    turns.append(turn2)
    print(f"  Tokens: {turn2.total_tokens} (cached: {turn2.cached_tokens})")
    if turn2.cached_tokens > 0:
        print(f"  ✅ Cache savings: {(turn2.cached_tokens/turn2.input_tokens)*100:.1f}%")
    
    # Turn 3: AML risk (should cache message context)
    print("\n[Turn 3] AML risk assessment...")
    prompt3 = "Assess the AML risk for this transaction. Are there any red flags?"
    turn3 = await run_turn(agent, prompt3, 3, api_type)
    turns.append(turn3)
    print(f"  Tokens: {turn3.total_tokens} (cached: {turn3.cached_tokens})")
    
    # Turn 4: Compliance report (should cache all prior analysis)
    print("\n[Turn 4] Generate compliance report...")
    prompt4 = "Generate a summary compliance report covering validation, conversion, and risk assessment."
    turn4 = await run_turn(agent, prompt4, 4, api_type)
    turns.append(turn4)
    print(f"  Tokens: {turn4.total_tokens} (cached: {turn4.cached_tokens})")
    
    return ScenarioResult(
        scenario_name="swift_analysis",
        api_type=api_type,
        endpoint=endpoint,
        turns=turns,
    )


# =============================================================================
# SCENARIO 4: Option Pricing with Greeks
# =============================================================================

async def scenario_option_analysis(endpoint: str, api_type: str) -> ScenarioResult:
    """Multi-turn option analysis - benefits: state retention, tool tracking."""
    print(f"\n{'='*60}")
    print(f"SCENARIO 4: Option Pricing + Greeks Analysis")
    print(f"API: {api_type.upper()} | Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    model = get_model_for_endpoint(endpoint, api_type)
    agent = Agent(model, system_prompt="You are a quantitative finance expert specializing in options.")
    
    turns = []
    
    # Turn 1: Price option
    print("\n[Turn 1] Price call option...")
    prompt1 = "Price a European call option: Spot price 100€, Strike 105€, Maturity 1 year, Risk-free rate 5%, Volatility 25%."
    turn1 = await run_turn(agent, prompt1, 1, api_type)
    turns.append(turn1)
    print(f"  Tokens: {turn1.total_tokens}")
    
    # Turn 2: Greeks (should cache option parameters)
    print("\n[Turn 2] Calculate Greeks...")
    prompt2 = "Calculate all the Greeks (Delta, Gamma, Theta, Vega, Rho) for this option."
    turn2 = await run_turn(agent, prompt2, 2, api_type)
    turns.append(turn2)
    print(f"  Tokens: {turn2.total_tokens} (cached: {turn2.cached_tokens})")
    
    # Turn 3: Scenario analysis (should cache base case)
    print("\n[Turn 3] Volatility scenario...")
    prompt3 = "What happens to the option price and Delta if volatility increases to 30%?"
    turn3 = await run_turn(agent, prompt3, 3, api_type)
    turns.append(turn3)
    print(f"  Tokens: {turn3.total_tokens} (cached: {turn3.cached_tokens})")
    
    # Turn 4: Hedge recommendation (uses all prior analysis)
    print("\n[Turn 4] Hedge strategy...")
    prompt4 = "Based on this analysis, recommend a delta-neutral hedging strategy."
    turn4 = await run_turn(agent, prompt4, 4, api_type)
    turns.append(turn4)
    print(f"  Tokens: {turn4.total_tokens} (cached: {turn4.cached_tokens})")
    
    return ScenarioResult(
        scenario_name="option_analysis",
        api_type=api_type,
        endpoint=endpoint,
        turns=turns,
    )


# =============================================================================
# COMPARISON AND ANALYSIS
# =============================================================================

def compare_results(chat_result: ScenarioResult, responses_result: ScenarioResult) -> Dict[str, Any]:
    """Compare Chat vs Responses API results."""
    
    # Calculate metrics
    token_reduction = ((chat_result.total_tokens - responses_result.total_tokens) / chat_result.total_tokens) * 100
    latency_change = ((responses_result.total_latency - chat_result.total_latency) / chat_result.total_latency) * 100
    
    # Cache metrics (Responses API only)
    cache_hit_rate = responses_result.cache_hit_rate
    
    comparison = {
        "scenario": chat_result.scenario_name,
        "endpoint": chat_result.endpoint,
        "chat": {
            "total_tokens": chat_result.total_tokens,
            "total_latency": chat_result.total_latency,
            "turns": len(chat_result.turns),
        },
        "responses": {
            "total_tokens": responses_result.total_tokens,
            "total_latency": responses_result.total_latency,
            "cached_tokens": responses_result.total_cached_tokens,
            "cache_hit_rate": cache_hit_rate,
            "turns": len(responses_result.turns),
        },
        "comparison": {
            "token_reduction_percent": token_reduction,
            "latency_change_percent": latency_change,
            "cache_effectiveness": cache_hit_rate,
        },
        "success_criteria": {
            "cache_hit_rate_target": 30.0,
            "cache_hit_rate_met": cache_hit_rate >= 30.0,
            "token_reduction_target": 15.0,
            "token_reduction_met": token_reduction >= 15.0,
            "latency_overhead_target": 20.0,
            "latency_acceptable": latency_change <= 20.0,
        }
    }
    
    return comparison


def print_comparison(comparison: Dict[str, Any]):
    """Pretty print comparison results."""
    print(f"\n{'='*60}")
    print(f"COMPARISON RESULTS: {comparison['scenario']}")
    print(f"{'='*60}")
    
    chat = comparison['chat']
    responses = comparison['responses']
    comp = comparison['comparison']
    criteria = comparison['success_criteria']
    
    print(f"\n📊 Token Usage:")
    print(f"  Chat API:      {chat['total_tokens']:,} tokens")
    print(f"  Responses API: {responses['total_tokens']:,} tokens")
    print(f"  Difference:    {comp['token_reduction_percent']:+.1f}%")
    print(f"  {'✅ PASSED' if criteria['token_reduction_met'] else '❌ FAILED'} (target: >{criteria['token_reduction_target']}%)")
    
    print(f"\n⚡ Latency:")
    print(f"  Chat API:      {chat['total_latency']:.2f}s")
    print(f"  Responses API: {responses['total_latency']:.2f}s")
    print(f"  Difference:    {comp['latency_change_percent']:+.1f}%")
    print(f"  {'✅ PASSED' if criteria['latency_acceptable'] else '❌ FAILED'} (target: <+{criteria['latency_overhead_target']}%)")
    
    print(f"\n💾 Cache Performance (Responses API):")
    print(f"  Cached tokens: {responses['cached_tokens']:,}")
    print(f"  Cache hit rate: {comp['cache_effectiveness']:.1f}%")
    print(f"  {'✅ PASSED' if criteria['cache_hit_rate_met'] else '❌ FAILED'} (target: >{criteria['cache_hit_rate_target']}%)")
    
    # Overall verdict
    print(f"\n{'='*60}")
    all_passed = (
        criteria['token_reduction_met'] and 
        criteria['cache_hit_rate_met'] and 
        criteria['latency_acceptable']
    )
    
    if all_passed:
        print("✅ VERDICT: Responses API shows clear benefits")
        print("   Recommendation: Proceed with full implementation")
    else:
        print("⚠️  VERDICT: Responses API benefits unclear")
        print("   Recommendation: Keep Chat Completions as default")
        
        if not criteria['token_reduction_met']:
            print("   - Token reduction below target")
        if not criteria['cache_hit_rate_met']:
            print("   - Cache hit rate below target")
        if not criteria['latency_acceptable']:
            print("   - Latency overhead too high")
    
    print(f"{'='*60}")
    
    return all_passed


# =============================================================================
# MAIN
# =============================================================================

SCENARIOS = {
    'portfolio': scenario_portfolio_optimization,
    'calculator': scenario_calculator_chain,
    'swift': scenario_swift_analysis,
    'option': scenario_option_analysis,
}


async def run_scenario(scenario_name: str, endpoint: str):
    """Run a scenario with both Chat and Responses APIs."""
    scenario_func = SCENARIOS[scenario_name]
    
    # Run with Chat API
    chat_result = await scenario_func(endpoint, "chat")
    
    # Run with Responses API
    responses_result = await scenario_func(endpoint, "responses")
    
    # Compare results
    comparison = compare_results(chat_result, responses_result)
    passed = print_comparison(comparison)
    
    return comparison, passed


async def main():
    parser = argparse.ArgumentParser(description='Test multi-turn scenarios to prove Responses API benefits')
    parser.add_argument('--endpoint', choices=['koyeb', 'hf', 'ollama'], default='ollama', help='Endpoint to test')
    parser.add_argument('--scenario', choices=list(SCENARIOS.keys()) + ['all'], default='all', help='Scenario to run')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Multi-Turn Scenario Testing: Chat vs Responses API")
    print("="*60)
    print(f"Endpoint: {args.endpoint}")
    print(f"Scenario: {args.scenario}")
    print("="*60)
    
    results = []
    
    if args.scenario == 'all':
        scenarios_to_run = list(SCENARIOS.keys())
    else:
        scenarios_to_run = [args.scenario]
    
    for scenario_name in scenarios_to_run:
        try:
            comparison, passed = await run_scenario(scenario_name, args.endpoint)
            results.append((scenario_name, comparison, passed))
        except Exception as e:
            print(f"\n❌ Error in scenario {scenario_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    total_passed = sum(1 for _, _, passed in results if passed)
    total_scenarios = len(results)
    
    print(f"\nScenarios passed: {total_passed}/{total_scenarios}")
    
    for scenario_name, comparison, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {scenario_name}")
    
    print(f"\n{'='*60}")
    if total_passed >= len(results) * 0.75:  # 75% pass rate
        print("✅ RECOMMENDATION: Proceed with full Responses API implementation")
        print("   Benefits proven across multiple scenarios")
    elif total_passed > 0:
        print("⚠️  RECOMMENDATION: Partial implementation")
        print("   Use Responses API only for scenarios that showed benefits")
    else:
        print("❌ RECOMMENDATION: Keep Chat Completions only")
        print("   No clear benefits demonstrated")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
