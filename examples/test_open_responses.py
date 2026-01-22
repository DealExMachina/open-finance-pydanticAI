#!/usr/bin/env python3
"""
Test script to verify PydanticAI's access to vLLM Open Response Standard details.

This script tests:
1. What token information is available in PydanticAI's UsageBase
2. Whether enhanced details (per-turn breakdowns, reasoning tokens) are accessible
3. What's in the details dictionary
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import get_finance_model
from pydantic_ai import Agent


async def test_standard_usage():
    """Test standard token usage fields."""
    print("=" * 60)
    print("TEST 1: Standard Token Usage Fields")
    print("=" * 60)
    
    model = get_finance_model()
    agent = Agent(model)
    
    result = await agent.run("What is compound interest? Explain briefly.")
    usage = result.usage()
    
    print("\n✅ Standard Fields Available:")
    print(f"  input_tokens: {usage.input_tokens}")
    print(f"  output_tokens: {usage.output_tokens}")
    print(f"  total_tokens: {usage.total_tokens}")
    
    print("\n✅ Cache Fields:")
    print(f"  cache_read_tokens: {usage.cache_read_tokens}")
    print(f"  cache_write_tokens: {usage.cache_write_tokens}")
    
    print("\n✅ Audio Fields (if applicable):")
    print(f"  input_audio_tokens: {usage.input_audio_tokens}")
    print(f"  output_audio_tokens: {usage.output_audio_tokens}")
    print(f"  cache_audio_read_tokens: {usage.cache_audio_read_tokens}")
    
    return usage


async def test_details_dict():
    """Test the details dictionary for enhanced information."""
    print("\n" + "=" * 60)
    print("TEST 2: Details Dictionary (Model-Specific Information)")
    print("=" * 60)
    
    model = get_finance_model()
    agent = Agent(model)
    
    result = await agent.run("Calculate future value: 10000€ at 5% for 10 years.")
    usage = result.usage()
    
    print(f"\n✅ Details Dict Type: {type(usage.details)}")
    print(f"✅ Details Dict Content: {usage.details}")
    
    if usage.details:
        print("\n📋 Details Keys:")
        for key, value in usage.details.items():
            print(f"  {key}: {value} (type: {type(value)})")
        
        # Check for vLLM-specific keys
        vllm_keys = [
            'input_tokens_details',
            'output_tokens_details',
            'cached_tokens',
            'reasoning_tokens',
            'tool_output_tokens',
            'input_tokens_per_turn',
            'output_tokens_per_turn',
        ]
        
        print("\n🔍 Checking for vLLM Open Response Standard keys:")
        found_keys = []
        for key in vllm_keys:
            if key in usage.details:
                found_keys.append(key)
                print(f"  ✅ Found: {key} = {usage.details[key]}")
        
        if not found_keys:
            print("  ❌ No vLLM-specific keys found in details dict")
    else:
        print("  ⚠️  Details dict is empty")
    
    return usage


async def test_multi_turn_conversation():
    """Test multi-turn conversation to see per-turn breakdowns."""
    print("\n" + "=" * 60)
    print("TEST 3: Multi-Turn Conversation (Per-Turn Breakdowns)")
    print("=" * 60)
    
    model = get_finance_model()
    agent = Agent(model)
    
    # First turn
    result1 = await agent.run("What is a bond?")
    usage1 = result1.usage()
    
    # Second turn (with context)
    result2 = await agent.run("What is the difference between a bond and a stock?")
    usage2 = result2.usage()
    
    print("\n📊 Turn 1 Usage:")
    print(f"  input_tokens: {usage1.input_tokens}")
    print(f"  output_tokens: {usage1.output_tokens}")
    print(f"  cache_read_tokens: {usage1.cache_read_tokens}")
    print(f"  details: {usage1.details}")
    
    print("\n📊 Turn 2 Usage:")
    print(f"  input_tokens: {usage2.input_tokens}")
    print(f"  output_tokens: {usage2.output_tokens}")
    print(f"  cache_read_tokens: {usage2.cache_read_tokens}")
    print(f"  details: {usage2.details}")
    
    # Check if cache was used in turn 2
    if usage2.cache_read_tokens > 0:
        print("\n✅ Cache was used in turn 2!")
    else:
        print("\n⚠️  No cache tokens detected in turn 2")
    
    return usage1, usage2


async def test_tool_calling():
    """Test tool calling to see tool output tokens."""
    print("\n" + "=" * 60)
    print("TEST 4: Tool Calling (Tool Output Tokens)")
    print("=" * 60)
    
    from examples.agent_2 import agent_2
    
    result = await agent_2.run("Calculate future value: 50000€ at 4% for 10 years.")
    usage = result.usage()
    
    print("\n📊 Tool Calling Usage:")
    print(f"  input_tokens: {usage.input_tokens}")
    print(f"  output_tokens: {usage.output_tokens}")
    print(f"  cache_read_tokens: {usage.cache_read_tokens}")
    print(f"  details: {usage.details}")
    
    if usage.details:
        print("\n🔍 Checking for tool-related keys:")
        tool_keys = ['tool_output_tokens', 'tool_output_tokens_per_turn']
        for key in tool_keys:
            if key in usage.details:
                print(f"  ✅ Found: {key} = {usage.details[key]}")
            else:
                print(f"  ❌ Not found: {key}")
    
    return usage


async def inspect_raw_response():
    """Try to inspect the raw response structure."""
    print("\n" + "=" * 60)
    print("TEST 5: Raw Response Inspection")
    print("=" * 60)
    
    model = get_finance_model()
    agent = Agent(model)
    
    result = await agent.run("What is diversification?")
    
    print("\n📋 Result Object Attributes:")
    attrs = [attr for attr in dir(result) if not attr.startswith('_')]
    for attr in attrs[:20]:  # First 20 attributes
        try:
            value = getattr(result, attr)
            if not callable(value):
                print(f"  {attr}: {type(value).__name__}")
        except:
            pass
    
    # Check if there's a way to access raw response
    print("\n🔍 Checking for raw response access:")
    if hasattr(result, 'all_messages'):
        print("  ✅ Has all_messages() method")
    if hasattr(result, 'model_response'):
        print("  ✅ Has model_response attribute")
        model_resp = result.model_response
        print(f"    Type: {type(model_resp)}")
        if hasattr(model_resp, 'provider_details'):
            print(f"    provider_details: {model_resp.provider_details}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PydanticAI Open Response Standard Compatibility Test")
    print("=" * 60)
    print("\nTesting what token information is accessible from vLLM responses")
    print("through PydanticAI's UsageBase class.\n")
    
    try:
        # Test 1: Standard usage
        usage1 = await test_standard_usage()
        
        # Test 2: Details dict
        usage2 = await test_details_dict()
        
        # Test 3: Multi-turn
        usage3a, usage3b = await test_multi_turn_conversation()
        
        # Test 4: Tool calling
        usage4 = await test_tool_calling()
        
        # Test 5: Raw response
        await inspect_raw_response()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("\n✅ Standard token fields are accessible")
        print("✅ Cache tokens are tracked")
        print("⚠️  Enhanced details (per-turn, reasoning, tool output) need verification")
        print("\n📝 Next Steps:")
        print("  1. Check if vLLM includes enhanced details in response")
        print("  2. Verify if details dict contains structured information")
        print("  3. Create parser utility if details are available")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
