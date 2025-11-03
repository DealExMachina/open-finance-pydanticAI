"""
Agent 1: Extraction et validation de données financières structurées

Cet agent démontre l'utilisation de PydanticAI pour extraire et valider
des données structurées à partir de textes financiers non structurés.
"""

import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# Modèles de données structurées
class PositionBoursiere(BaseModel):
    """Représente une position boursière."""
    symbole: str = Field(description="Symbole de l'action (ex: AIR.PA, SAN.PA)")
    quantite: int = Field(description="Nombre d'actions", ge=0)
    prix_achat: float = Field(description="Prix d'achat unitaire en euros", ge=0)
    date_achat: str = Field(description="Date d'achat au format YYYY-MM-DD")


class Portfolio(BaseModel):
    """Portfolio avec positions boursières."""
    positions: list[PositionBoursiere] = Field(description="Liste des positions")
    valeur_totale: float = Field(description="Valeur totale du portfolio en euros", ge=0)
    date_evaluation: str = Field(description="Date d'évaluation")


# Agent pour extraction de données structurées
extract_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1200),  # Sufficient for structured data extraction
    system_prompt=(
        "Vous êtes un assistant expert en analyse de données financières. "
        "Votre rôle est d'extraire des informations structurées à partir "
        "de textes non structurés concernant des portfolios d'actions françaises. "
        "Identifiez les symboles, quantités, prix d'achat et dates. "
        "Calculez la valeur totale du portfolio."
    ),
)


async def exemple_extraction_portfolio():
    """Exemple d'extraction de données de portfolio."""
    texte_non_structure = """
    Mon portfolio actuel :
    - J'ai acheté 50 actions Airbus (AIR.PA) à 120€ le 15 mars 2024
    - 30 actions Sanofi (SAN.PA) à 85€ le 20 février 2024  
    - 100 actions TotalEnergies (TTE.PA) à 55€ le 10 janvier 2024
    
    Date d'évaluation : 1er novembre 2024
    """
    
    print("📊 Agent 1: Extraction de données structurées")
    print("=" * 60)
    print(f"Texte d'entrée:\n{texte_non_structure}\n")
    
    result = await extract_agent.run(
        f"Extrais les informations du portfolio suivant et formate-les de manière structurée:\n{texte_non_structure}\n\n"
        "Réponds avec:\n- Le nombre de positions\n- Les détails de chaque position (symbole, quantité, prix, date)\n- La valeur totale estimée"
    )
    
    # Parser la réponse texte (simplifié pour l'exemple)
    response = result.output
    # En production, on utiliserait output_type=Portfolio pour validation automatique
    print("✅ Résultat structuré:")
    print(response)
    print("\n💡 Note: Avec output_type=Portfolio, PydanticAI validerait")
    print("   automatiquement la structure et fournirait un objet typé.")
    
    return response


if __name__ == "__main__":
    asyncio.run(exemple_extraction_portfolio())

