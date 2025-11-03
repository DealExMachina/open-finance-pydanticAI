"""
Agent 3: Workflow multi-étapes avec agents spécialisés

Cet agent démontre la création d'un workflow où plusieurs agents spécialisés
collaborent pour résoudre un problème financier complexe.
"""

import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# Agents spécialisés avec limites appropriées
risk_analyst = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1200),  # Risk analysis
    system_prompt=(
        "Vous êtes un analyste de risque financier. "
        "Vous évaluez les risques associés à différents instruments financiers "
        "et stratégies d'investissement. "
        "Fournissez une évaluation de risque sur 5 niveaux (1=très faible, 5=très élevé)."
    ),
)

tax_advisor = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1500),  # Tax advice can be detailed
    system_prompt=(
        "Vous êtes un conseiller fiscal français. "
        "Vous expliquez les implications fiscales des investissements "
        "selon la réglementation française (PEA, assurance-vie, compte-titres, etc.)."
    ),
)

portfolio_optimizer = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),  # Portfolio optimization can be complex
    system_prompt=(
        "Vous êtes un optimiseur de portfolio. "
        "Vous proposez des allocations d'actifs optimisées "
        "en fonction des objectifs, de l'horizon temporel et du profil de risque. "
        "Répondez toujours en français."
    ),
)


class AnalyseRisque(BaseModel):
    """Analyse de risque."""
    niveau_risque: int = Field(description="Niveau de risque de 1 à 5", ge=1, le=5)
    facteurs_risque: list[str] = Field(description="Liste des facteurs de risque identifiés")
    recommandation: str = Field(description="Recommandation basée sur le niveau de risque")


async def workflow_analyse_investissement():
    """Workflow multi-étapes pour analyser un investissement."""
    print("\n🔄 Agent 3: Workflow multi-étapes")
    print("=" * 60)
    
    scenario = """
    Un investisseur de 35 ans avec un profil modéré souhaite investir 100 000€.
    Objectif: Préparer la retraite dans 30 ans.
    Il envisage:
    - 40% en actions françaises (CAC 40)
    - 30% en obligations d'État
    - 20% en immobiler via SCPI
    - 10% en cryptomonnaies
    
    Analysez ce portfolio du point de vue:
    1. Risque
    2. Fiscalité
    3. Optimisation
    """
    
    print("Scénario:\n", scenario, "\n")
    
    # Étape 1: Analyse de risque
    print("📊 Étape 1: Analyse de risque...")
    risk_result = await risk_analyst.run(
        f"Analyse le niveau de risque (1-5) de cette stratégie:\n{scenario}\n\n"
        "Fournis: niveau de risque (1-5), facteurs de risque principaux, et recommandation."
    )
    risk_output = risk_result.output
    print(f"  Analyse:\n  {risk_output[:300]}...\n")
    
    # Étape 2: Conseil fiscal
    print("💰 Étape 2: Analyse fiscale...")
    tax_result = await tax_advisor.run(
        f"Quelles sont les implications fiscales de cette stratégie d'investissement "
        f"en France?\n{scenario}"
    )
    print(f"  Conseil fiscal:\n  {tax_result.output[:300]}...\n")
    
    # Étape 3: Optimisation avec contexte des étapes précédentes
    print("🎯 Étape 3: Optimisation du portfolio...")
    optimization_result = await portfolio_optimizer.run(
        f"""
        Scénario: {scenario}
        
        Analyses précédentes:
        - Analyse de risque: {risk_output[:200]}
        - Analyse fiscale: {tax_result.output[:200]}
        
        Propose une allocation optimisée en tenant compte de ces analyses.
        """
    )
    print(f"  Recommandation d'optimisation:\n  {optimization_result.output[:400]}...\n")
    
    # Résumé final
    print("✅ Workflow terminé avec succès!")
    print(f"  - Analyse de risque: Complétée")
    print(f"  - Conseils fiscaux: Fournis")
    print(f"  - Optimisation: Recommandation générée")


async def exemple_agent_simple():
    """Exemple simplifié d'un agent qui fait tout en une étape."""
    print("\n🚀 Agent 3 (Variante): Agent tout-en-un")
    print("=" * 60)
    
    multi_agent = Agent(
        finance_model,
        model_settings=ModelSettings(max_output_tokens=2000),  # Complete analysis needs more tokens
        system_prompt=(
            "Vous êtes un conseiller financier complet. "
            "Pour chaque demande d'analyse, fournissez:\n"
            "1. Une évaluation du risque (1-5)\n"
            "2. Les implications fiscales en France\n"
            "3. Une recommandation d'optimisation\n"
            "Répondez toujours en français de manière structurée."
        ),
    )
    
    question = (
        "J'ai 50 000€ à investir avec un horizon de 15 ans. "
        "Je pense à 60% actions, 30% obligations, 10% immobilier. "
        "Analysez cette stratégie."
    )
    
    result = await multi_agent.run(question)
    print(f"Question: {question}\n")
    print(f"Analyse complète:\n{result.output[:500]}...")


if __name__ == "__main__":
    print("Exécution du workflow multi-étapes...")
    asyncio.run(workflow_analyse_investissement())
    
    print("\n\n" + "=" * 60)
    asyncio.run(exemple_agent_simple())

