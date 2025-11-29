"""
Exemple d'utilisation des stratégies de mitigation avec agents fine-tunés (Qwen 8B).

Démontre comment appliquer les stratégies de mitigation pour:
1. Détecter les tool calls manquants
2. Valider les formats JSON
3. Valider la sémantique
4. Implémenter des retries intelligents
"""

import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model
from app.mitigation_strategies import (
    SafeAgent,
    ToolCallDetector,
    JSONValidator,
    RetryStrategy,
    create_portfolio_validator,
    create_calculation_validator,
    with_tool_call_validation,
    with_json_validation,
)

# Import des outils existants
try:
    from examples.agent_2 import (
        calculer_valeur_future,
        calculer_versement_mensuel,
        calculer_performance_portfolio,
    )
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from examples.agent_2 import (
        calculer_valeur_future,
        calculer_versement_mensuel,
        calculer_performance_portfolio,
    )


# ============================================================================
# MODÈLES DE DONNÉES
# ============================================================================

class PortfolioExtraction(BaseModel):
    """Modèle pour extraction de portfolio."""
    positions: list[dict] = Field(description="Liste des positions")
    valeur_totale: float = Field(description="Valeur totale", ge=0)
    date_evaluation: str = Field(description="Date d'évaluation")


# ============================================================================
# AGENT AVEC OUTILS
# ============================================================================

base_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),
    system_prompt=(
        "Vous êtes un conseiller financier expert avec accès à des outils de calcul financier précis.\n\n"
        "RÈGLES CRITIQUES:\n"
        "1. VOUS DEVEZ TOUJOURS utiliser les outils disponibles pour TOUS les calculs financiers\n"
        "2. NE CALCULEZ JAMAIS manuellement - utilisez TOUJOURS les outils\n"
        "3. Pour calculer une valeur future → utilisez calculer_valeur_future\n"
        "4. Pour calculer un versement mensuel → utilisez calculer_versement_mensuel\n\n"
        "N'expliquez pas comment calculer - UTILISEZ LES OUTILS directement."
    ),
    tools=[
        calculer_valeur_future,
        calculer_versement_mensuel,
        calculer_performance_portfolio,
    ],
)


# ============================================================================
# EXEMPLE 1: Agent sécurisé avec validation de tool calls
# ============================================================================

async def exemple_1_tool_call_validation():
    """Exemple 1: Validation des tool calls."""
    print("\n" + "=" * 80)
    print("EXEMPLE 1: Validation des Tool Calls")
    print("=" * 80)
    
    # Créer un agent sécurisé qui exige des tool calls
    safe_agent = SafeAgent(
        agent=base_agent,
        tool_call_required=True,
        expected_tools=["calculer_valeur_future"],
        max_retries=3
    )
    
    question = "J'ai 50 000€ à 4% par an pendant 10 ans. Combien aurai-je?"
    
    print(f"\nQuestion: {question}\n")
    
    result, success, errors = await safe_agent.run_safe(question)
    
    print(f"✅ Succès: {success}")
    if errors:
        print(f"❌ Erreurs: {', '.join(errors)}")
    
    # Vérifier les tool calls
    tool_calls = ToolCallDetector.extract_tool_calls(result) or []
    print(f"\n📊 Tool calls détectés: {len(tool_calls)}")
    if tool_calls:
        for i, tc in enumerate(tool_calls, 1):
            print(f"  {i}. {tc['name']} avec args: {tc['args']}")
    else:
        print("  ⚠️ Aucun tool call détecté")
    
    print(f"\n📝 Réponse:\n{result.output}\n")


# ============================================================================
# EXEMPLE 2: Agent avec validation JSON
# ============================================================================

extraction_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),
    system_prompt=(
        "Vous êtes un expert en extraction de données financières. "
        "Extrayez les informations de portfolio et répondez UNIQUEMENT avec un JSON valide."
    ),
)

async def exemple_2_json_validation():
    """Exemple 2: Validation des sorties JSON."""
    print("\n" + "=" * 80)
    print("EXEMPLE 2: Validation des Sorties JSON")
    print("=" * 80)
    
    # Créer un agent sécurisé avec validation JSON
    safe_agent = SafeAgent(
        agent=extraction_agent,
        output_type=PortfolioExtraction,
        max_retries=3,
        semantic_validator=create_portfolio_validator()
    )
    
    prompt = """Extrais le portfolio suivant en JSON:
    - 50 actions Airbus (AIR.PA) à 120€
    - 30 actions Sanofi (SAN.PA) à 85€
    - 100 actions TotalEnergies (TTE.PA) à 55€
    Valeur totale: 18,500€
    Date: 2024-11-01"""
    
    print(f"\nPrompt: {prompt}\n")
    
    result, success, errors = await safe_agent.run_safe(prompt)
    
    print(f"✅ Succès: {success}")
    if errors:
        print(f"❌ Erreurs: {', '.join(errors)}")
    
    if success and hasattr(result, 'data') and result.data:
        print(f"\n📊 Données validées:")
        print(f"  Positions: {len(result.data.positions)}")
        print(f"  Valeur totale: {result.data.valeur_totale:,.2f}€")
        print(f"  Date: {result.data.date_evaluation}")
    
    print(f"\n📝 Réponse brute:\n{result.output[:500]}...\n")


# ============================================================================
# EXEMPLE 3: Retry avec prompts alternatifs
# ============================================================================

async def exemple_3_retry_with_fallback():
    """Exemple 3: Retry avec prompts de fallback."""
    print("\n" + "=" * 80)
    print("EXEMPLE 3: Retry avec Prompts de Fallback")
    print("=" * 80)
    
    prompts = [
        # Prompt initial (spécifique)
        "Calcule la valeur future de 25 000€ à 5% pendant 8 ans. Utilise l'outil calculer_valeur_future.",
        # Prompt de fallback 1 (plus explicite)
        "QUESTION: Calcule la valeur future.\n"
        "PARAMÈTRES:\n"
        "- Capital initial: 25 000€\n"
        "- Taux annuel: 5% (0.05)\n"
        "- Durée: 8 ans\n"
        "ACTION REQUISE: Appelle l'outil calculer_valeur_future avec ces paramètres.",
        # Prompt de fallback 2 (très explicite)
        "Tu DOIS appeler l'outil calculer_valeur_future avec:\n"
        "capital_initial=25000, taux_annuel=0.05, duree_annees=8\n"
        "Ne calcule pas manuellement, utilise l'outil."
    ]
    
    result, success = await RetryStrategy.retry_with_fallback_prompt(
        agent=base_agent,
        prompts=prompts,
        output_type=None
    )
    
    print(f"✅ Succès: {success}")
    
    # Vérifier les tool calls
    tool_calls = ToolCallDetector.extract_tool_calls(result) or []
    print(f"📊 Tool calls détectés: {len(tool_calls)}")
    if tool_calls:
        for i, tc in enumerate(tool_calls, 1):
            print(f"  {i}. {tc.get('name', 'unknown')}")
    
    print(f"\n📝 Réponse:\n{result.output}\n")


# ============================================================================
# EXEMPLE 4: Validation complète (tool calls + JSON + sémantique)
# ============================================================================

async def exemple_4_validation_complete():
    """Exemple 4: Validation complète avec tous les mécanismes."""
    print("\n" + "=" * 80)
    print("EXEMPLE 4: Validation Complète (Tool Calls + JSON + Sémantique)")
    print("=" * 80)
    
    # Agent avec extraction JSON
    json_agent = Agent(
        finance_model,
        model_settings=ModelSettings(max_output_tokens=2000),
        system_prompt=(
            "Extrais les informations de portfolio et réponds avec un JSON valide. "
            "Assure-toi que la valeur totale correspond à la somme des positions."
        ),
    )
    
    safe_agent = SafeAgent(
        agent=json_agent,
        output_type=PortfolioExtraction,
        tool_call_required=False,  # Pas d'outils pour cet agent
        max_retries=3,
        semantic_validator=create_portfolio_validator()
    )
    
    prompt = """Extrais le portfolio suivant:
    Portfolio au 1er novembre 2024:
    - 50 actions Airbus (AIR.PA) achetées à 120€
    - 30 actions Sanofi (SAN.PA) achetées à 85€
    - 100 actions TotalEnergies (TTE.PA) achetées à 55€
    
    Valeur totale: 18,500€ (50*120 + 30*85 + 100*55 = 18,500€)"""
    
    print(f"\nPrompt: {prompt}\n")
    
    result, success, errors = await safe_agent.run_safe(prompt)
    
    print(f"✅ Succès: {success}")
    if errors:
        print(f"❌ Erreurs: {', '.join(errors)}")
    
    # Afficher les détails
    if success and hasattr(result, 'data') and result.data:
        print(f"\n📊 Données extraites et validées:")
        print(f"  Nombre de positions: {len(result.data.positions)}")
        print(f"  Valeur totale: {result.data.valeur_totale:,.2f}€")
        
        # Vérifier la cohérence
        somme = sum(
            p.get("quantite", 0) * p.get("prix_achat", 0)
            for p in result.data.positions
            if isinstance(p, dict)
        )
        print(f"  Somme des positions: {somme:,.2f}€")
        print(f"  Cohérence: {'✅' if abs(somme - result.data.valeur_totale) < 100 else '❌'}")
    
    print(f"\n📝 Réponse:\n{result.output[:500]}...\n")


# ============================================================================
# EXEMPLE 5: Utilisation des décorateurs
# ============================================================================

@with_tool_call_validation(expected_tools=["calculer_valeur_future"], min_calls=1)
@with_json_validation(output_type=None)  # Pas de JSON pour cet exemple
async def exemple_5_decorators(question: str):
    """Exemple 5: Utilisation des décorateurs de validation."""
    print("\n" + "=" * 80)
    print("EXEMPLE 5: Utilisation des Décorateurs")
    print("=" * 80)
    
    print(f"\nQuestion: {question}\n")
    
    result = await base_agent.run(question)
    
    print(f"📝 Réponse:\n{result.output}\n")
    
    return result


# ============================================================================
# EXÉCUTION DES EXEMPLES
# ============================================================================

async def main():
    """Exécute tous les exemples."""
    await exemple_1_tool_call_validation()
    await asyncio.sleep(1)
    
    await exemple_2_json_validation()
    await asyncio.sleep(1)
    
    await exemple_3_retry_with_fallback()
    await asyncio.sleep(1)
    
    await exemple_4_validation_complete()
    await asyncio.sleep(1)
    
    await exemple_5_decorators(
        "J'ai 30 000€ à 4.5% pendant 12 ans. Combien aurai-je?"
    )


if __name__ == "__main__":
    asyncio.run(main())

