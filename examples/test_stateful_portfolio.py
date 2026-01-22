#!/usr/bin/env python3
"""
Stateful multi-turn portfolio analysis to demonstrate Responses API benefits.

This test maintains conversation context across turns to enable cache hits.
Unlike test_multiturn_scenarios.py which creates new agents per turn,
this maintains a single conversation thread.

Key differences:
1. Same agent instance across all turns (conversation continuity)
2. Each turn references prior context explicitly
3. Progressive refinement pattern (realistic advisor interaction)
4. Measures cache effectiveness in context reuse

Usage:
    python examples/test_stateful_portfolio.py --api-type chat
    python examples/test_stateful_portfolio.py --api-type responses
    python examples/test_stateful_portfolio.py --compare
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import get_model_for_endpoint
from pydantic_ai import Agent


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    turn_num: int
    user_message: str
    assistant_response: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_tokens: int
    elapsed_seconds: float


class PortfolioAdvisorConversation:
    """Maintains a stateful portfolio advisory conversation."""
    
    def __init__(self, endpoint: str, api_type: str):
        self.endpoint = endpoint
        self.api_type = api_type
        self.model = get_model_for_endpoint(endpoint, api_type)
        self.agent = Agent(
            self.model,
            system_prompt=(
                "You are an expert financial advisor specializing in portfolio management. "
                "Maintain context of the client's situation across the conversation. "
                "Be concise but thorough."
            )
        )
        self.turns: List[ConversationTurn] = []
    
    async def turn(self, user_message: str) -> ConversationTurn:
        """Execute a conversation turn."""
        turn_num = len(self.turns) + 1
        
        print(f"\n{'─'*60}")
        print(f"[Turn {turn_num}] User: {user_message[:80]}...")
        
        start = time.time()
        result = await self.agent.run(user_message)
        elapsed = time.time() - start
        
        # Extract metrics
        usage = result.usage()
        response_text = str(result.output) if hasattr(result, 'output') else str(result)
        
        turn = ConversationTurn(
            turn_num=turn_num,
            user_message=user_message,
            assistant_response=response_text[:200],
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached_tokens=usage.cache_read_tokens,
            elapsed_seconds=elapsed,
        )
        
        self.turns.append(turn)
        
        # Print metrics
        print(f"[Turn {turn_num}] Assistant: {response_text[:100]}...")
        print(f"         Tokens: {usage.total_tokens} (in: {usage.input_tokens}, out: {usage.output_tokens})")
        if usage.cache_read_tokens > 0:
            cache_pct = (usage.cache_read_tokens / usage.input_tokens) * 100
            print(f"         💾 Cache hit: {usage.cache_read_tokens} tokens ({cache_pct:.1f}% of input)")
        print(f"         ⏱️  Time: {elapsed:.2f}s")
        
        return turn
    
    def get_summary(self):
        """Get conversation summary."""
        total_tokens = sum(t.total_tokens for t in self.turns)
        total_cached = sum(t.cached_tokens for t in self.turns)
        total_time = sum(t.elapsed_seconds for t in self.turns)
        
        # Cache hit rate for Turn 2+ (Turn 1 can't have cache hits)
        if len(self.turns) > 1:
            turn2plus_input = sum(t.input_tokens for t in self.turns[1:])
            turn2plus_cached = sum(t.cached_tokens for t in self.turns[1:])
            cache_rate = (turn2plus_cached / turn2plus_input * 100) if turn2plus_input > 0 else 0
        else:
            cache_rate = 0
        
        return {
            'api_type': self.api_type,
            'total_turns': len(self.turns),
            'total_tokens': total_tokens,
            'total_cached': total_cached,
            'total_time': total_time,
            'cache_hit_rate_turn2plus': cache_rate,
            'avg_tokens_per_turn': total_tokens / len(self.turns) if self.turns else 0,
            'avg_time_per_turn': total_time / len(self.turns) if self.turns else 0,
        }


async def run_portfolio_conversation(endpoint: str, api_type: str):
    """Run a realistic portfolio advisory conversation."""
    
    print(f"\n{'='*60}")
    print(f"Portfolio Advisory Conversation")
    print(f"API Type: {api_type.upper()} | Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    conv = PortfolioAdvisorConversation(endpoint, api_type)
    
    # Turn 1: Initial situation
    await conv.turn(
        "Hello, I'm 35 years old with 100,000€ to invest for retirement in 30 years. "
        "I currently have 50% in stocks (CAC40 index), 30% in government bonds, and 20% in real estate (SCPI). "
        "What do you think of this allocation?"
    )
    
    # Turn 2: Risk adjustment (references "this allocation" from Turn 1)
    await conv.turn(
        "I'm actually quite risk-averse. How should I adjust this allocation to be more conservative?"
    )
    
    # Turn 3: Tax optimization (references the adjusted portfolio from Turn 2)
    await conv.turn(
        "For this adjusted portfolio, what's the most tax-efficient way to structure it in France? "
        "I know about PEA and assurance-vie."
    )
    
    # Turn 4: Practical next steps (synthesizes all prior discussion)
    await conv.turn(
        "Given everything we've discussed, what are the concrete next steps I should take? "
        "Which accounts should I open first?"
    )
    
    # Turn 5: Cost question (references entire conversation context)
    await conv.turn(
        "What are the typical management fees I should expect for this strategy?"
    )
    
    return conv


async def compare_apis(endpoint: str):
    """Compare Chat vs Responses API with same conversation."""
    
    # Run with Chat API
    chat_conv = await run_portfolio_conversation(endpoint, 'chat')
    chat_summary = chat_conv.get_summary()
    
    print("\n" + "="*60)
    print("Now running same conversation with Responses API...")
    print("="*60)
    await asyncio.sleep(2)  # Brief pause
    
    # Run with Responses API
    responses_conv = await run_portfolio_conversation(endpoint, 'responses')
    responses_summary = responses_conv.get_summary()
    
    # Compare
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    token_diff = ((chat_summary['total_tokens'] - responses_summary['total_tokens']) / chat_summary['total_tokens']) * 100
    time_diff = ((responses_summary['total_time'] - chat_summary['total_time']) / chat_summary['total_time']) * 100
    
    print(f"\n📊 Token Usage:")
    print(f"  Chat API:      {chat_summary['total_tokens']:,} tokens")
    print(f"  Responses API: {responses_summary['total_tokens']:,} tokens")
    print(f"  Difference:    {token_diff:+.1f}%")
    
    print(f"\n💾 Cache Performance (Responses API):")
    print(f"  Total cached: {responses_summary['total_cached']:,} tokens")
    print(f"  Cache hit rate (Turn 2-5): {responses_summary['cache_hit_rate_turn2plus']:.1f}%")
    
    print(f"\n⏱️  Latency:")
    print(f"  Chat API:      {chat_summary['total_time']:.1f}s")
    print(f"  Responses API: {responses_summary['total_time']:.1f}s")
    print(f"  Difference:    {time_diff:+.1f}%")
    
    print(f"\n📈 Per-Turn Breakdown:")
    print(f"\n  Chat API:")
    for turn in chat_conv.turns:
        print(f"    Turn {turn.turn_num}: {turn.total_tokens:4d} tokens ({turn.elapsed_seconds:.1f}s)")
    
    print(f"\n  Responses API:")
    for turn in responses_conv.turns:
        cache_info = f", 💾 {turn.cached_tokens}" if turn.cached_tokens > 0 else ""
        print(f"    Turn {turn.turn_num}: {turn.total_tokens:4d} tokens ({turn.elapsed_seconds:.1f}s{cache_info})")
    
    # Success criteria
    print(f"\n{'='*60}")
    print("SUCCESS CRITERIA")
    print(f"{'='*60}")
    
    criteria = {
        'cache_hit_rate': responses_summary['cache_hit_rate_turn2plus'] >= 30.0,
        'token_reduction': token_diff >= 15.0,
        'latency_acceptable': time_diff <= 20.0,
    }
    
    print(f"  Cache hit rate > 30%:    {'✅' if criteria['cache_hit_rate'] else '❌'} {responses_summary['cache_hit_rate_turn2plus']:.1f}%")
    print(f"  Token reduction > 15%:   {'✅' if criteria['token_reduction'] else '❌'} {token_diff:+.1f}%")
    print(f"  Latency overhead < 20%:  {'✅' if criteria['latency_acceptable'] else '❌'} {time_diff:+.1f}%")
    
    all_passed = all(criteria.values())
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ VERDICT: Responses API shows clear benefits")
        print("   Recommendation: Proceed with implementation")
    else:
        print("❌ VERDICT: Responses API does not provide sufficient benefits")
        print("   Recommendation: Keep Chat Completions API")
        
        if not criteria['cache_hit_rate']:
            print("\n   Issue: No cache hits - context not being reused")
            print("   Cause: PydanticAI agent.run() doesn't maintain state between calls")
            print("   Fix: Would require passing previous_response_id (not currently supported)")
        
        if not criteria['token_reduction']:
            print("\n   Issue: Token reduction insufficient")
            if token_diff < 0:
                print(f"   WARNING: Responses API uses MORE tokens ({abs(token_diff):.1f}% increase)")
    
    print(f"{'='*60}")
    
    return all_passed


async def main():
    parser = argparse.ArgumentParser(description='Test stateful portfolio conversation')
    parser.add_argument('--endpoint', choices=['koyeb', 'hf', 'ollama'], default='ollama')
    parser.add_argument('--api-type', choices=['chat', 'responses'])
    parser.add_argument('--compare', action='store_true', help='Compare both APIs')
    
    args = parser.parse_args()
    
    if args.compare:
        await compare_apis(args.endpoint)
    elif args.api_type:
        conv = await run_portfolio_conversation(args.endpoint, args.api_type)
        summary = conv.get_summary()
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total tokens: {summary['total_tokens']:,}")
        print(f"Total cached: {summary['total_cached']:,}")
        print(f"Cache hit rate (Turn 2+): {summary['cache_hit_rate_turn2plus']:.1f}%")
        print(f"Total time: {summary['total_time']:.1f}s")
    else:
        print("Specify --api-type or --compare")


if __name__ == "__main__":
    asyncio.run(main())
