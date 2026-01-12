"""Unified observability layer for Langfuse and Logfire.

This module provides a single interface for tracing PydanticAI agent runs
to both Langfuse and Logfire platforms. Users can enable one, the other,
or both platforms via configuration or runtime toggles.

Usage:
    from app.observability import get_observability_handler, configure_observability
    
    # Configure at startup
    configure_observability()
    
    # Get handler for agent runs
    handler = get_observability_handler()
    result = await handler.trace_agent_run(agent, prompt, agent_name, endpoint)
"""

import logging
import time
from typing import Any, Dict, Optional, Type
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Global state for observability
_observability_configured = False
_runtime_overrides: Dict[str, bool] = {}


@dataclass
class ObservabilityState:
    """Tracks the state of observability platforms."""
    langfuse_enabled: bool = False
    langfuse_configured: bool = False
    logfire_enabled: bool = False
    logfire_configured: bool = False
    pydantic_ai_instrumented: bool = False


_state = ObservabilityState()


def configure_observability() -> ObservabilityState:
    """
    Configure both Langfuse and Logfire based on settings.
    
    Should be called once at application startup.
    
    Returns:
        ObservabilityState with configuration status.
    """
    global _observability_configured, _state
    
    if _observability_configured:
        return _state
    
    from app.config import settings
    
    # Configure Langfuse
    _state.langfuse_enabled = getattr(settings, 'enable_langfuse', True)
    if _state.langfuse_enabled:
        try:
            from app.langfuse_config import configure_langfuse, get_langfuse_client
            configure_langfuse()
            _state.langfuse_configured = get_langfuse_client() is not None
            if _state.langfuse_configured:
                logger.info("Langfuse configured and ready")
            else:
                logger.info("Langfuse enabled but not configured (missing credentials)")
        except Exception as e:
            logger.warning(f"Failed to configure Langfuse: {e}")
            _state.langfuse_configured = False
    else:
        logger.info("Langfuse disabled via configuration")
    
    # Configure Logfire
    _state.logfire_enabled = getattr(settings, 'enable_logfire', True)
    if _state.logfire_enabled:
        try:
            from app.logfire_config import configure_logfire, instrument_pydantic_ai
            _state.logfire_configured = configure_logfire()
            if _state.logfire_configured:
                _state.pydantic_ai_instrumented = instrument_pydantic_ai()
                logger.info("Logfire configured and PydanticAI instrumented")
            else:
                logger.info("Logfire enabled but not configured (missing token)")
        except Exception as e:
            logger.warning(f"Failed to configure Logfire: {e}")
            _state.logfire_configured = False
    else:
        logger.info("Logfire disabled via configuration")
    
    _observability_configured = True
    return _state


def get_observability_state() -> ObservabilityState:
    """Get the current observability state."""
    if not _observability_configured:
        configure_observability()
    return _state


def set_runtime_override(platform: str, enabled: bool) -> None:
    """
    Set a runtime override for a platform.
    
    This allows the UI to temporarily enable/disable platforms
    without changing the configuration.
    
    Args:
        platform: "langfuse" or "logfire"
        enabled: Whether to enable the platform
    """
    _runtime_overrides[platform] = enabled
    logger.info(f"Runtime override: {platform} = {enabled}")


def clear_runtime_overrides() -> None:
    """Clear all runtime overrides."""
    _runtime_overrides.clear()


def is_langfuse_active() -> bool:
    """Check if Langfuse is currently active (configured and enabled)."""
    state = get_observability_state()
    if "langfuse" in _runtime_overrides:
        return _runtime_overrides["langfuse"] and state.langfuse_configured
    return state.langfuse_enabled and state.langfuse_configured


def is_logfire_active() -> bool:
    """Check if Logfire is currently active (configured and enabled)."""
    state = get_observability_state()
    if "logfire" in _runtime_overrides:
        return _runtime_overrides["logfire"] and state.logfire_configured
    return state.logfire_enabled and state.logfire_configured


class ObservabilityHandler:
    """
    Unified handler for tracing agent runs to both Langfuse and Logfire.
    
    Logfire uses automatic instrumentation via logfire.instrument_pydantic_ai(),
    so most tracing happens automatically. This handler adds Langfuse tracing
    on top for detailed span management.
    """
    
    def __init__(
        self,
        agent_name: str = "unknown_agent",
        endpoint: str = "unknown",
        enable_langfuse: Optional[bool] = None,
        enable_logfire: Optional[bool] = None,
    ):
        """
        Initialize the handler.
        
        Args:
            agent_name: Name of the agent being traced
            endpoint: Endpoint being used (koyeb, hf, etc.)
            enable_langfuse: Override for Langfuse (None = use config/runtime)
            enable_logfire: Override for Logfire (None = use config/runtime)
        """
        self.agent_name = agent_name
        self.endpoint = endpoint
        
        # Determine which platforms to use
        self._use_langfuse = enable_langfuse if enable_langfuse is not None else is_langfuse_active()
        self._use_logfire = enable_logfire if enable_logfire is not None else is_logfire_active()
        
        # Initialize Langfuse handler if needed
        self._langfuse_handler = None
        if self._use_langfuse:
            try:
                from app.langfuse_integration import LangfusePydanticAIHandler
                self._langfuse_handler = LangfusePydanticAIHandler(agent_name, endpoint)
            except Exception as e:
                logger.warning(f"Failed to create Langfuse handler: {e}")
                self._use_langfuse = False
    
    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse is enabled for this handler."""
        return self._use_langfuse and self._langfuse_handler is not None
    
    @property
    def logfire_enabled(self) -> bool:
        """Check if Logfire is enabled for this handler."""
        return self._use_logfire
    
    async def trace_agent_run(
        self,
        agent,
        prompt: str,
        output_type: Optional[Type[BaseModel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Run an agent and trace the execution to enabled platforms.
        
        Logfire tracing is automatic via instrumentation.
        Langfuse tracing uses the existing handler for detailed spans.
        
        Args:
            agent: PydanticAI Agent instance
            prompt: Input prompt/question
            output_type: Optional output type for structured outputs
            metadata: Additional metadata to attach to traces
            
        Returns:
            Agent run result
        """
        # Merge metadata
        full_metadata = {
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            **(metadata or {}),
        }
        
        # If Langfuse is enabled, use its handler (which also runs the agent)
        if self._use_langfuse and self._langfuse_handler:
            return await self._langfuse_handler.trace_agent_run(
                agent, prompt, output_type, full_metadata
            )
        
        # Otherwise, just run the agent (Logfire auto-instruments if enabled)
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
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, run without Langfuse tracing
                # (Logfire still works via auto-instrumentation)
                if output_type:
                    return asyncio.create_task(agent.run(prompt, output_type=output_type))
                return asyncio.create_task(agent.run(prompt))
            else:
                return loop.run_until_complete(
                    self.trace_agent_run(agent, prompt, output_type, metadata)
                )
        except RuntimeError:
            return asyncio.run(
                self.trace_agent_run(agent, prompt, output_type, metadata)
            )


def get_observability_handler(
    agent_name: str = "unknown_agent",
    endpoint: str = "unknown",
) -> ObservabilityHandler:
    """
    Get an observability handler for tracing agent runs.
    
    Args:
        agent_name: Name of the agent
        endpoint: Endpoint being used
        
    Returns:
        Configured ObservabilityHandler instance
    """
    # Ensure observability is configured
    if not _observability_configured:
        configure_observability()
    
    return ObservabilityHandler(agent_name=agent_name, endpoint=endpoint)


def get_status_summary() -> Dict[str, Any]:
    """
    Get a summary of observability status for display in UI.
    
    Returns:
        Dictionary with status information for each platform.
    """
    state = get_observability_state()
    
    return {
        "langfuse": {
            "enabled": state.langfuse_enabled,
            "configured": state.langfuse_configured,
            "active": is_langfuse_active(),
            "runtime_override": _runtime_overrides.get("langfuse"),
        },
        "logfire": {
            "enabled": state.logfire_enabled,
            "configured": state.logfire_configured,
            "active": is_logfire_active(),
            "pydantic_ai_instrumented": state.pydantic_ai_instrumented,
            "runtime_override": _runtime_overrides.get("logfire"),
        },
    }
