"""Langfuse integration for PydanticAI agents."""

import logging
import time
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from app.langfuse_config import get_langfuse_client
from app.mitigation_strategies import ToolCallDetector

logger = logging.getLogger(__name__)


class LangfusePydanticAIHandler:
    """Handler for tracing PydanticAI agent runs with Langfuse."""
    
    def __init__(self, agent_name: str = "unknown_agent", endpoint: str = "unknown"):
        """Initialize the handler.
        
        Args:
            agent_name: Name of the agent (e.g., "Agent 1", "finance_agent")
            endpoint: Endpoint used (e.g., "koyeb", "hf", "llm_pro_finance")
        """
        self.agent_name = agent_name
        self.endpoint = endpoint
        self.langfuse = get_langfuse_client()
    
    def _is_enabled(self) -> bool:
        """Check if Langfuse is enabled and configured."""
        return self.langfuse is not None
    
    async def trace_agent_run(
        self,
        agent,
        prompt: str,
        output_type: Optional[Type[BaseModel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Run an agent and trace the execution with Langfuse.
        
        Args:
            agent: PydanticAI Agent instance
            prompt: Input prompt/question
            output_type: Optional output type for structured outputs
            metadata: Additional metadata to attach to the trace
            
        Returns:
            Agent run result (same as agent.run())
        """
        if not self._is_enabled():
            # Langfuse not configured, run agent normally
            if output_type:
                return await agent.run(prompt, output_type=output_type)
            return await agent.run(prompt)
        
        start_time = time.time()
        trace = None
        span = None
        
        try:
            # Create trace
            trace = self.langfuse.trace(
                name=f"agent_{self.agent_name}",
                metadata={
                    "agent_name": self.agent_name,
                    "endpoint": self.endpoint,
                    "has_output_type": output_type is not None,
                    **(metadata or {}),
                },
            )
            
            # Create span for the agent run
            span = trace.span(
                name="agent_execution",
                metadata={
                    "prompt": prompt[:500],  # Truncate long prompts
                    "output_type": str(output_type) if output_type else None,
                },
            )
            
            # Run the agent
            if output_type:
                result = await agent.run(prompt, output_type=output_type)
            else:
                result = await agent.run(prompt)
            
            elapsed_time = time.time() - start_time
            
            # Extract token usage
            usage = None
            try:
                usage_func = getattr(result, 'usage', None)
                if callable(usage_func):
                    usage = usage_func()
                elif usage_func:
                    usage = usage_func
            except Exception as e:
                logger.debug(f"Error extracting usage: {e}")
            
            # Extract tool calls
            tool_calls = ToolCallDetector.extract_tool_calls(result) if hasattr(result, 'all_messages') else []
            
            # Update span with results
            span.end(
                output={
                    "output": str(result.output)[:1000] if hasattr(result, 'output') else str(result)[:1000],
                    "tool_calls_count": len(tool_calls),
                    "tool_names": [tc.get('name', 'unknown') for tc in tool_calls],
                },
                metadata={
                    "elapsed_time": elapsed_time,
                    "input_tokens": getattr(usage, 'input_tokens', 0) if usage else 0,
                    "output_tokens": getattr(usage, 'output_tokens', 0) if usage else 0,
                    "total_tokens": getattr(usage, 'total_tokens', 0) if usage else 0,
                },
            )
            
            # Create spans for tool calls
            if tool_calls:
                for i, tool_call in enumerate(tool_calls):
                    tool_span = span.span(
                        name=f"tool_{tool_call.get('name', 'unknown')}",
                        metadata={
                            "tool_name": tool_call.get('name', 'unknown'),
                            "arguments": tool_call.get('args', {}),
                        },
                    )
                    # Try to extract tool result if available
                    tool_result = None
                    try:
                        if hasattr(result, 'all_messages'):
                            for msg in result.all_messages():
                                msg_calls = getattr(msg, "tool_calls", None) or []
                                for call in msg_calls:
                                    if hasattr(call, 'result'):
                                        tool_result = str(call.result)[:500]
                                        break
                    except Exception:
                        pass
                    
                    tool_span.end(
                        output=tool_result or "Tool executed",
                    )
            
            # Create LLM generation span
            # PydanticAI doesn't expose internal LLM calls directly, so we create a summary span
            if hasattr(result, 'all_messages'):
                messages = list(result.all_messages())
                llm_span = span.span(
                    name="llm_generation",
                    metadata={
                        "message_count": len(messages),
                    },
                )
                
                # Extract conversation history for context
                conversation_summary = []
                for msg in messages[:5]:  # Limit to first 5 messages
                    role = getattr(msg, 'role', 'unknown')
                    content = str(getattr(msg, 'content', ''))[:200] if hasattr(msg, 'content') else ''
                    conversation_summary.append(f"{role}: {content[:200]}")
                
                llm_span.end(
                    output={
                        "conversation_summary": conversation_summary,
                        "total_messages": len(messages),
                    },
                    metadata={
                        "input_tokens": getattr(usage, 'input_tokens', 0) if usage else 0,
                        "output_tokens": getattr(usage, 'output_tokens', 0) if usage else 0,
                    },
                )
            
            # End trace
            trace.update(
                output={
                    "agent_output": str(result.output)[:1000] if hasattr(result, 'output') else str(result)[:1000],
                    "success": True,
                },
                metadata={
                    "elapsed_time": elapsed_time,
                    "total_tokens": getattr(usage, 'total_tokens', 0) if usage else 0,
                    "tool_calls_count": len(tool_calls),
                },
            )
            
            return result
            
        except Exception as e:
            # Log error but don't fail the agent execution
            logger.warning(f"Error in Langfuse tracing: {e}", exc_info=True)
            
            if span:
                span.end(
                    output={"error": str(e)},
                    level="ERROR",
                )
            
            if trace:
                trace.update(
                    output={"success": False, "error": str(e)},
                    level="ERROR",
                )
            
            # Still run the agent even if tracing fails
            if output_type:
                return await agent.run(prompt, output_type=output_type)
            return await agent.run(prompt)
    
    def trace_sync_agent_run(
        self,
        agent,
        prompt: str,
        output_type: Optional[Type[BaseModel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Synchronous wrapper for trace_agent_run.
        
        This is a convenience method for use in synchronous contexts.
        Note: This will create a new event loop if one doesn't exist.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use a different approach
                # For now, just run without tracing
                logger.warning("Event loop already running, skipping Langfuse tracing")
                if output_type:
                    # This won't work in a running loop, but we try
                    return asyncio.create_task(agent.run(prompt, output_type=output_type))
                return asyncio.create_task(agent.run(prompt))
            else:
                return loop.run_until_complete(
                    self.trace_agent_run(agent, prompt, output_type, metadata)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(
                self.trace_agent_run(agent, prompt, output_type, metadata)
            )

