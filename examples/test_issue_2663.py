#!/usr/bin/env python3
"""
Minimal reproducible test case for PydanticAI issue #2663:
https://github.com/pydantic/pydantic-ai/issues/2663

Demonstrates that OpenAIResponsesModel doesn't pass previous_response_id,
resulting in 0% cache hits even with stateful conversations.

Expected behavior:
- Turn 2+ should have cache hits when using Responses API
- previous_response_id should be passed automatically

Actual behavior:
- 0% cache hits on all turns
- previous_response_id is never passed
- Each turn treated as new conversation

Test with:
    # Ollama (local)
    pip install pydantic-ai
    ollama pull qwen2.5:3b
    python test_issue_2663.py
    
    # OpenAI (if you have API key)
    export OPENAI_API_KEY=your-key
    python test_issue_2663.py --openai
"""

import argparse
import asyncio
import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


async def test_with_message_history(model_class, model_name: str, base_url: str, api_key: str):
    """Test multi-turn conversation with message_history."""
    
    api_type = "Responses" if model_class == OpenAIResponsesModel else "Chat"
    
    print(f"\n{'='*60}")
    print(f"{api_type} API - 3 Turn Conversation with message_history")
    print(f"{'='*60}")
    
    # Create model
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    model = model_class(model_name=model_name, provider=provider)
    agent = Agent(model, system_prompt="You are a helpful assistant. Be concise.")
    
    # Initialize message history
    message_history = []
    
    # Turn 1
    print("\n[Turn 1] User: Tell me about compound interest.")
    result1 = await agent.run("Tell me about compound interest.", message_history=message_history)
    message_history.extend(result1.new_messages())
    
    usage1 = result1.usage()
    print(f"         Tokens: {usage1.total_tokens} (in: {usage1.input_tokens}, out: {usage1.output_tokens})")
    print(f"         Cached: {usage1.cache_read_tokens}")
    
    # Turn 2 (references "it" from Turn 1)
    print("\n[Turn 2] User: Can you explain it with an example?")
    result2 = await agent.run("Can you explain it with an example?", message_history=message_history)
    message_history.extend(result2.new_messages())
    
    usage2 = result2.usage()
    print(f"         Tokens: {usage2.total_tokens} (in: {usage2.input_tokens}, out: {usage2.output_tokens})")
    print(f"         Cached: {usage2.cache_read_tokens}")
    
    if usage2.cache_read_tokens > 0:
        cache_pct = (usage2.cache_read_tokens / usage2.input_tokens) * 100
        print(f"         💾 Cache hit! {cache_pct:.1f}% of input tokens cached")
    else:
        print(f"         ⚠️  NO cache hits (expected >0 for Responses API)")
    
    # Turn 3 (references example from Turn 2)
    print("\n[Turn 3] User: What's the formula for that example?")
    result3 = await agent.run("What's the formula for that example?", message_history=message_history)
    
    usage3 = result3.usage()
    print(f"         Tokens: {usage3.total_tokens} (in: {usage3.input_tokens}, out: {usage3.output_tokens})")
    print(f"         Cached: {usage3.cache_read_tokens}")
    
    if usage3.cache_read_tokens > 0:
        cache_pct = (usage3.cache_read_tokens / usage3.input_tokens) * 100
        print(f"         💾 Cache hit! {cache_pct:.1f}% of input tokens cached")
    else:
        print(f"         ⚠️  NO cache hits (expected >0 for Responses API)")
    
    # Summary
    total_tokens = usage1.total_tokens + usage2.total_tokens + usage3.total_tokens
    total_cached = usage1.cache_read_tokens + usage2.cache_read_tokens + usage3.cache_read_tokens
    
    print(f"\n{'─'*60}")
    print(f"SUMMARY ({api_type} API):")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Total cached: {total_cached}")
    print(f"  Cache hit rate: {(total_cached/total_tokens*100):.1f}%")
    
    return {
        'api_type': api_type,
        'total_tokens': total_tokens,
        'total_cached': total_cached,
        'cache_hit_rate': (total_cached/total_tokens*100) if total_tokens > 0 else 0,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--openai', action='store_true', help='Test with OpenAI (requires API key)')
    args = parser.parse_args()
    
    if args.openai:
        # Test with OpenAI
        if not os.getenv('OPENAI_API_KEY'):
            print("Error: Set OPENAI_API_KEY environment variable")
            return
        
        model_name = "gpt-4o-mini"
        base_url = "https://api.openai.com/v1"
        api_key = os.getenv('OPENAI_API_KEY')
    else:
        # Test with Ollama (local)
        model_name = "qwen2.5:3b-instruct"
        base_url = "http://localhost:11434/v1"
        api_key = "ollama"
    
    print("="*60)
    print("PydanticAI Issue #2663 - Minimal Reproduction")
    print("="*60)
    print(f"Model: {model_name}")
    print(f"Endpoint: {base_url}")
    
    # Test Chat API
    chat_result = await test_with_message_history(
        OpenAIChatModel,
        model_name,
        base_url,
        api_key
    )
    
    # Test Responses API
    responses_result = await test_with_message_history(
        OpenAIResponsesModel,
        model_name,
        base_url,
        api_key
    )
    
    # Compare
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")
    print(f"Chat API cache hits:      {chat_result['total_cached']} ({chat_result['cache_hit_rate']:.1f}%)")
    print(f"Responses API cache hits: {responses_result['total_cached']} ({responses_result['cache_hit_rate']:.1f}%)")
    
    print(f"\n{'='*60}")
    print("EXPECTED vs ACTUAL")
    print(f"{'='*60}")
    print("Expected: Responses API should have cache hits on Turn 2-3")
    print("          when using message_history (via previous_response_id)")
    print(f"Actual:   {responses_result['total_cached']} cache hits (0%)")
    print("\nConclusion: previous_response_id is not being passed by PydanticAI")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
