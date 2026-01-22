#!/usr/bin/env python3
"""
Test script to verify vLLM Responses API support and OpenAIResponsesModel compatibility.

This script tests:
1. If vLLM exposes /v1/responses endpoint
2. If OpenAIResponsesModel works with vLLM
3. Enhanced token details availability with Responses API
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.config import settings, ENDPOINTS
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


async def test_responses_endpoint():
    """Test if vLLM exposes the Responses API endpoint."""
    print("=" * 60)
    print("TEST 1: vLLM Responses API Endpoint Availability")
    print("=" * 60)
    
    endpoint = "koyeb"
    endpoint_config = ENDPOINTS.get(endpoint, {})
    base_url = endpoint_config.get("url", "")
    
    if not base_url:
        print("❌ No endpoint configured")
        return False
    
    # Test /v1/responses endpoint
    responses_url = f"{base_url}/v1/responses"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try OPTIONS or GET to check if endpoint exists
            response = await client.get(responses_url)
            print(f"\n📡 Testing: {responses_url}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 404:
                print("   ❌ Endpoint not found - vLLM may not support Responses API")
                return False
            elif response.status_code in [200, 401, 405]:
                print("   ✅ Endpoint exists! (405 = Method Not Allowed is OK)")
                return True
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_openai_responses_model():
    """Test OpenAIResponsesModel with vLLM."""
    print("\n" + "=" * 60)
    print("TEST 2: OpenAIResponsesModel with vLLM")
    print("=" * 60)
    
    endpoint = "koyeb"
    endpoint_config = ENDPOINTS.get(endpoint, {})
    base_url = endpoint_config.get("url", "")
    model_name = endpoint_config.get("model", "DragonLLM/Qwen-Open-Finance-R-8B")
    
    try:
        # Create OpenAIResponsesModel
        model = OpenAIResponsesModel(
            model_name=model_name,
            provider=OpenAIProvider(
                base_url=f"{base_url}/v1",
                api_key=settings.api_key,
            ),
        )
        
        print(f"\n✅ Created OpenAIResponsesModel")
        print(f"   Model: {model_name}")
        print(f"   Base URL: {base_url}/v1")
        
        # Create agent
        agent = Agent(model)
        
        # Test run
        print("\n🔄 Running test query...")
        result = await agent.run("What is compound interest? Explain briefly.")
        
        print("✅ Agent run successful!")
        print(f"   Output: {str(result.output)[:200]}...")
        
        # Check usage
        usage = result.usage()
        print(f"\n📊 Token Usage:")
        print(f"   input_tokens: {usage.input_tokens}")
        print(f"   output_tokens: {usage.output_tokens}")
        print(f"   cache_read_tokens: {usage.cache_read_tokens}")
        print(f"   cache_write_tokens: {usage.cache_write_tokens}")
        print(f"   details: {usage.details}")
        
        # Check ModelResponse
        if hasattr(result, 'model_response'):
            model_resp = result.model_response
            print(f"\n📋 ModelResponse:")
            print(f"   provider_name: {model_resp.provider_name}")
            print(f"   provider_details: {model_resp.provider_details}")
            print(f"   finish_reason: {model_resp.finish_reason}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def compare_models():
    """Compare OpenAIChatModel vs OpenAIResponsesModel."""
    print("\n" + "=" * 60)
    print("TEST 3: Compare Chat vs Responses API")
    print("=" * 60)
    
    endpoint = "koyeb"
    endpoint_config = ENDPOINTS.get(endpoint, {})
    base_url = endpoint_config.get("url", "")
    model_name = endpoint_config.get("model", "DragonLLM/Qwen-Open-Finance-R-8B")
    
    provider = OpenAIProvider(
        base_url=f"{base_url}/v1",
        api_key=settings.api_key,
    )
    
    prompt = "Calculate future value: 10000€ at 5% for 10 years."
    
    # Test Chat API
    print("\n1️⃣  Testing OpenAIChatModel (Chat Completions API):")
    try:
        chat_model = OpenAIChatModel(model_name=model_name, provider=provider)
        chat_agent = Agent(chat_model)
        chat_result = await chat_agent.run(prompt)
        chat_usage = chat_result.usage()
        
        print(f"   ✅ Success")
        print(f"   input_tokens: {chat_usage.input_tokens}")
        print(f"   output_tokens: {chat_usage.output_tokens}")
        print(f"   details: {chat_usage.details}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Responses API
    print("\n2️⃣  Testing OpenAIResponsesModel (Responses API):")
    try:
        responses_model = OpenAIResponsesModel(model_name=model_name, provider=provider)
        responses_agent = Agent(responses_model)
        responses_result = await responses_agent.run(prompt)
        responses_usage = responses_result.usage()
        
        print(f"   ✅ Success")
        print(f"   input_tokens: {responses_usage.input_tokens}")
        print(f"   output_tokens: {responses_usage.output_tokens}")
        print(f"   details: {responses_usage.details}")
        
        # Check for enhanced details
        if hasattr(responses_result, 'model_response'):
            provider_details = responses_result.model_response.provider_details
            print(f"   provider_details: {provider_details}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   Note: vLLM may not support Responses API endpoint")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("vLLM Responses API & OpenAIResponsesModel Compatibility Test")
    print("=" * 60)
    print("\nTesting Open Response Standard support through OpenAIResponsesModel\n")
    
    # Test 1: Endpoint availability
    endpoint_available = await test_responses_endpoint()
    
    # Test 2: OpenAIResponsesModel
    if endpoint_available:
        await test_openai_responses_model()
    else:
        print("\n⚠️  Skipping OpenAIResponsesModel test - endpoint not available")
    
    # Test 3: Comparison
    await compare_models()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\n✅ OpenAIResponsesModel is available in PydanticAI 1.44.0")
    if endpoint_available:
        print("✅ vLLM Responses API endpoint is available")
        print("✅ Can use OpenAIResponsesModel for Open Response Standard support")
    else:
        print("⚠️  vLLM Responses API endpoint not available")
        print("   - May need vLLM configuration to enable Responses API")
        print("   - Fallback to OpenAIChatModel with provider_details parsing")
    
    print("\n📝 Next Steps:")
    print("   1. Verify vLLM server configuration for Responses API")
    print("   2. Test OpenAIResponsesModel if endpoint is available")
    print("   3. Compare token details between Chat and Responses APIs")


if __name__ == "__main__":
    asyncio.run(main())
