"""
Custom vLLM-compatible provider for PydanticAI.

This provider wraps OpenAIProvider to support vLLM's structured outputs format.
When output_type is used, it converts tool-based requests to vLLM's extra_body format.
"""

import json
from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic_ai.providers.openai import OpenAIProvider


class VLLMCompatibleClient:
    """
    Wrapper around AsyncOpenAI that intercepts chat.completions.create calls
    to convert tool-based structured outputs to vLLM's format.
    """
    
    def __init__(self, client: AsyncOpenAI, is_vllm: bool = False):
        self._client = client
        self._is_vllm = is_vllm
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying client."""
        if name == 'chat':
            return VLLMChatWrapper(self._client.chat, self._is_vllm)
        return getattr(self._client, name)
    
    @property
    def base_url(self):
        return self._client.base_url


class VLLMChatWrapper:
    """Wrapper for chat.completions that handles vLLM conversion."""
    
    def __init__(self, chat_obj: Any, is_vllm: bool):
        self._chat = chat_obj
        self._is_vllm = is_vllm
        # Delegate completions
        self.completions = VLLMCompletionsWrapper(chat_obj.completions, is_vllm)


class VLLMCompletionsWrapper:
    """Wrapper for chat.completions.create."""
    
    def __init__(self, completions_obj: Any, is_vllm: bool):
        self._completions = completions_obj
        self._is_vllm = is_vllm
    
    async def create(self, **kwargs) -> ChatCompletion:
        """Intercept create call and convert for vLLM if needed."""
        if not self._is_vllm:
            # Not vLLM, pass through
            return await self._completions.create(**kwargs)
        
        # Check if this is a structured output request (tool_choice="required")
        tool_choice = kwargs.get("tool_choice")
        tools = kwargs.get("tools")
        
        if tool_choice == "required" and tools and len(tools) == 1:
            # Convert to vLLM format
            tool = tools[0]
            function = tool.get("function", {})
            parameters = function.get("parameters", {})
            tool_name = function.get("name", "extract_data")
            
            if parameters:
                # Convert to vLLM's extra_body format
                extra_body = kwargs.get("extra_body", {})
                if not isinstance(extra_body, dict):
                    extra_body = {}
                
                extra_body["structured_outputs"] = {
                    "json": parameters
                }
                kwargs["extra_body"] = extra_body
                
                # Remove tools and tool_choice (vLLM doesn't need them)
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                
                # Make the request
                response = await self._completions.create(**kwargs)
                
                # Convert response back to tool call format
                return self._convert_response_to_tool_call(response, tool_name)
        
        # Not a structured output request, pass through
        return await self._completions.create(**kwargs)
    
    def _convert_response_to_tool_call(
        self, 
        response: ChatCompletion, 
        tool_name: str
    ) -> ChatCompletion:
        """Convert vLLM's JSON-in-content response to tool call format."""
        if not response.choices:
            return response
        
        choice = response.choices[0]
        message = choice.message
        content = message.content
        
        # If content is JSON, convert to tool call
        if content and content.strip().startswith("{"):
            try:
                # Validate JSON
                json.loads(content)
                
                # Create tool call
                from openai.types.chat import ChatCompletionMessageToolCall
                from openai.types.chat.chat_completion_message_function_tool_call import Function
                import uuid
                
                tool_call = ChatCompletionMessageToolCall(
                    id=f"call_{uuid.uuid4().hex[:16]}",
                    type="function",
                    function=Function(
                        name=tool_name,
                        arguments=content
                    )
                )
                
                # Create new message with tool_calls (ChatCompletion objects are immutable)
                from openai.types.chat import ChatCompletionMessage
                new_message = ChatCompletionMessage(
                    role=message.role,
                    content=None,
                    tool_calls=[tool_call],
                    refusal=message.refusal if hasattr(message, 'refusal') else None,
                )
                
                # Create new choice
                from openai.types.chat.chat_completion import Choice
                new_choice = Choice(
                    index=choice.index,
                    message=new_message,
                    finish_reason="tool_calls",
                    logprobs=choice.logprobs,
                )
                
                # Create new response
                return ChatCompletion(
                    id=response.id,
                    choices=[new_choice],
                    created=response.created,
                    model=response.model,
                    object=response.object,
                    usage=response.usage,
                    service_tier=getattr(response, 'service_tier', None),
                    system_fingerprint=getattr(response, 'system_fingerprint', None),
                )
                
            except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
                # If conversion fails, leave as-is
                print(f"⚠️  Failed to convert vLLM response to tool call: {e}")
                pass
        
        return response


class VLLMProvider(OpenAIProvider):
    """
    vLLM-compatible provider that converts PydanticAI's tool-based structured outputs
    to vLLM's extra_body.structured_outputs format.
    """
    
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        openai_client: AsyncOpenAI | None = None,
        http_client: Any | None = None,
    ):
        """Initialize vLLM provider."""
        # Detect if this is a vLLM endpoint
        is_vllm = self._detect_vllm_endpoint(base_url or (openai_client.base_url if openai_client else None))
        
        # If we have an existing client, wrap it
        if openai_client:
            wrapped_client = VLLMCompatibleClient(openai_client, is_vllm)
            super().__init__(openai_client=wrapped_client, http_client=http_client)
        else:
            # Create new client and wrap it
            super().__init__(base_url=base_url, api_key=api_key, http_client=http_client)
            if is_vllm:
                # Wrap the client after creation
                original_client = self._client
                self._client = VLLMCompatibleClient(original_client, is_vllm)
    
    @staticmethod
    def _detect_vllm_endpoint(base_url: Optional[str]) -> bool:
        """Detect if the endpoint is vLLM based on URL patterns."""
        if not base_url:
            return False
        # vLLM endpoints typically contain "koyeb" or can be detected by checking /models
        vllm_indicators = ["koyeb", "vllm", "localhost:8000"]
        base_url_lower = str(base_url).lower()
        return any(indicator in base_url_lower for indicator in vllm_indicators)

