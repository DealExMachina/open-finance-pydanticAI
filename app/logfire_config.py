"""Configuration Logfire pour le projet open-finance dans l'organisation deal-ex-machina (UE).

Provides automatic instrumentation for PydanticAI agents when enabled.
"""

import logging
import logfire
from app.config import settings

logger = logging.getLogger(__name__)

# Flags to track configuration state
_logfire_configured = False
_pydantic_ai_instrumented = False


def configure_logfire(send_to_logfire: bool | str | None = 'if-token-present') -> bool:
    """
    Configure Logfire pour le projet open-finance dans l'organisation deal-ex-machina.
    
    Le projet est configuré pour la région UE pour la conformité RGPD.
    
    Args:
        send_to_logfire: Si 'if-token-present', n'envoie que si un token est présent.
                        Si False, désactive complètement l'envoi.
                        Si True, force l'envoi (nécessite authentification).
    
    Returns:
        True if Logfire was configured successfully, False otherwise.
    """
    global _logfire_configured
    
    if _logfire_configured:
        return True
    
    # Check if Logfire is enabled in settings
    enable_logfire = getattr(settings, 'enable_logfire', True)
    if not enable_logfire:
        logger.info("Logfire is disabled via configuration (ENABLE_LOGFIRE=false)")
        _logfire_configured = True
        return False
    
    try:
        logfire.configure(
            service_name="open-finance-pydanticai",
            service_version="0.1.0",
            environment=getattr(settings, 'environment', 'development'),
            send_to_logfire=send_to_logfire,
            # Le token est automatiquement récupéré depuis:
            # - Variable d'environnement LOGFIRE_TOKEN
            # - Ou via logfire auth (stocké dans .logfire/)
            # Le projet et l'organisation sont déterminés par le token
            # Pour le projet "open-finance" dans "deal-ex-machina", exécutez:
            # logfire auth
        )
        
        _logfire_configured = True
        logger.info("Logfire configured successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to configure Logfire: {e}. Continuing without Logfire.")
        _logfire_configured = True
        return False


def instrument_pydantic_ai() -> bool:
    """
    Instrument PydanticAI agents with Logfire for automatic tracing.
    
    This should be called after configure_logfire() and before creating agents.
    It automatically traces all PydanticAI agent runs, tool calls, and LLM generations.
    
    Returns:
        True if instrumentation was successful, False otherwise.
    """
    global _pydantic_ai_instrumented
    
    if _pydantic_ai_instrumented:
        return True
    
    # Ensure Logfire is configured first
    if not _logfire_configured:
        configure_logfire()
    
    # Check if Logfire is enabled
    enable_logfire = getattr(settings, 'enable_logfire', True)
    if not enable_logfire:
        logger.info("Skipping PydanticAI instrumentation - Logfire disabled")
        _pydantic_ai_instrumented = True
        return False
    
    try:
        # Instrument all PydanticAI agents
        logfire.instrument_pydantic_ai()
        _pydantic_ai_instrumented = True
        logger.info("PydanticAI agents instrumented with Logfire")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to instrument PydanticAI with Logfire: {e}")
        _pydantic_ai_instrumented = True
        return False


def is_logfire_enabled() -> bool:
    """Check if Logfire is enabled and configured."""
    return _logfire_configured and getattr(settings, 'enable_logfire', True)


def is_pydantic_ai_instrumented() -> bool:
    """Check if PydanticAI agents are instrumented with Logfire."""
    return _pydantic_ai_instrumented and is_logfire_enabled()

