"""
Agent 2: Agent avec outils (Tools) pour calculs financiers

Cet agent démontre l'utilisation d'outils Python que l'agent peut appeler
pour effectuer des calculs financiers complexes.
"""

import asyncio
from typing import Annotated
from pydantic import BaseModel
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# Outils que l'agent peut utiliser
def calculer_valeur_future(
    capital_initial: float,
    taux_annuel: float,
    duree_annees: float
) -> str:
    """Calcule la valeur future avec intérêts composés.
    
    Args:
        capital_initial: Montant initial en euros
        taux_annuel: Taux d'intérêt annuel (ex: 0.05 pour 5%)
        duree_annees: Durée en années
    
    Returns:
        Valeur future calculée
    """
    valeur_future = capital_initial * (1 + taux_annuel) ** duree_annees
    interets = valeur_future - capital_initial
    return (
        f"Valeur future: {valeur_future:,.2f}€\n"
        f"Intérêts générés: {interets:,.2f}€\n"
        f"Capital initial: {capital_initial:,.2f}€"
    )


def calculer_versement_mensuel(
    capital_emprunte: float,
    taux_annuel: float,
    duree_mois: int
) -> str:
    """Calcule le versement mensuel pour un prêt.
    
    Args:
        capital_emprunte: Montant emprunté en euros
        taux_annuel: Taux d'intérêt annuel (ex: 0.04 pour 4%)
        duree_mois: Durée du prêt en mois
    
    Returns:
        Versement mensuel calculé
    """
    taux_mensuel = taux_annuel / 12
    versement = capital_emprunte * (
        taux_mensuel * (1 + taux_mensuel) ** duree_mois
    ) / ((1 + taux_mensuel) ** duree_mois - 1)
    
    total_rembourse = versement * duree_mois
    cout_total = total_rembourse - capital_emprunte
    
    return (
        f"Versement mensuel: {versement:,.2f}€\n"
        f"Total remboursé: {total_rembourse:,.2f}€\n"
        f"Coût total du crédit: {cout_total:,.2f}€"
    )


def calculer_performance_portfolio(
    valeur_initiale: float,
    valeur_actuelle: float,
    duree_jours: int
) -> str:
    """Calcule la performance d'un portfolio.
    
    Args:
        valeur_initiale: Valeur initiale en euros
        valeur_actuelle: Valeur actuelle en euros
        duree_jours: Durée en jours
    
    Returns:
        Performance calculée
    """
    gain_absolu = valeur_actuelle - valeur_initiale
    gain_pourcentage = (gain_absolu / valeur_initiale) * 100
    rendement_annuelise = ((valeur_actuelle / valeur_initiale) ** (365 / duree_jours) - 1) * 100
    
    return (
        f"Gain absolu: {gain_absolu:+,.2f}€ ({gain_pourcentage:+.2f}%)\n"
        f"Rendement annualisé: {rendement_annuelise:+.2f}%\n"
        f"Durée: {duree_jours} jours"
    )


# Agent avec outils
finance_calculator_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1500),  # For explanations with calculations
    system_prompt=(
        "Vous êtes un conseiller financier expert. "
        "Quand un client vous pose une question nécessitant un calcul financier, "
        "utilisez les outils de calcul disponibles pour fournir des résultats précis. "
        "Expliquez toujours les résultats dans le contexte de la question du client. "
        "Répondez en français."
    ),
    tools=[calculer_valeur_future, calculer_versement_mensuel, calculer_performance_portfolio],
)


async def exemple_agent_avec_outils():
    """Exemple d'utilisation d'un agent avec outils."""
    print("\n🔧 Agent 2: Agent avec outils de calcul")
    print("=" * 60)
    
    question = (
        "J'ai un capital de 50 000€ que je veux placer à 4% par an pendant 10 ans. "
        "Combien aurai-je à la fin ? Et si j'emprunte 200 000€ sur 20 ans à 3.5% "
        "pour acheter un appartement, combien paierai-je par mois ?"
    )
    
    print(f"Question:\n{question}\n")
    
    result = await finance_calculator_agent.run(question)
    
    print("✅ Réponse de l'agent avec calculs:")
    print(result.output)
    print()
    
    # Afficher quels outils ont été utilisés
    if hasattr(result, 'usage') and result.usage:
        print("📊 Utilisation des outils:")
        print(f"  - Tokens utilisés: {result.usage.total_tokens if hasattr(result.usage, 'total_tokens') else 'N/A'}")


if __name__ == "__main__":
    asyncio.run(exemple_agent_avec_outils())

