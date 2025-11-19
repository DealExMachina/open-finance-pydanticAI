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


# Agent pour extraction de données structurées avec prompt optimisé pour petit modèle
extract_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1200),
    system_prompt=(
        "Tu es un expert en analyse financière. Tu extrais des données de portfolios boursiers.\n\n"
        "RÈGLES STRICTES:\n"
        "1. Lis attentivement le texte fourni\n"
        "2. Identifie TOUTES les positions avec: symbole, quantité, prix d'achat, date\n"
        "3. Calcule la valeur totale: somme de (quantité × prix_achat) pour chaque position\n"
        "4. Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après\n\n"
        "EXEMPLE de réponse attendue:\n"
        '{\n'
        '  "positions": [\n'
        '    {"symbole": "AIR.PA", "quantite": 50, "prix_achat": 120.0, "date_achat": "2024-03-15"},\n'
        '    {"symbole": "SAN.PA", "quantite": 30, "prix_achat": 85.0, "date_achat": "2024-02-20"}\n'
        '  ],\n'
        '  "valeur_totale": 8550.0,\n'
        '  "date_evaluation": "2024-11-01"\n'
        '}\n\n'
        "IMPORTANT: Génère UNIQUEMENT le JSON, commence par { et termine par }"
    ),
)


async def exemple_extraction_portfolio():
    """Exemple d'extraction de données de portfolio avec validation Pydantic."""
    texte_non_structure = """
    Mon portfolio actuel :
    - J'ai acheté 50 actions Airbus (AIR.PA) à 120€ le 15 mars 2024
    - 30 actions Sanofi (SAN.PA) à 85€ le 20 février 2024  
    - 100 actions TotalEnergies (TTE.PA) à 55€ le 10 janvier 2024
    
    Date d'évaluation : 1er novembre 2024
    """
    
    print("📊 Agent 1: Extraction de données structurées avec PydanticAI")
    print("=" * 70)
    print(f"Texte d'entrée:\n{texte_non_structure}\n")
    
    # Prompt optimisé pour modèle 8B
    prompt = (
        f"Extrais les données du portfolio suivant en JSON:\n\n"
        f"{texte_non_structure}\n\n"
        f"Pour chaque action, fournis: symbole, quantite, prix_achat, date_achat (YYYY-MM-DD).\n"
        f"Calcule la valeur_totale (somme de quantite × prix_achat).\n"
        f"Utilise la date_evaluation donnée."
    )
    
    try:
        # Utilisation de output_type pour validation automatique
        result = await extract_agent.run(prompt, output_type=Portfolio)
        
        # Vérifier si result.data existe (validation réussie)
        portfolio = None
        try:
            portfolio = result.data
        except AttributeError:
            # result.data n'existe pas, essayer de parser result.output
            pass
        
        if portfolio:
            print("✅ Extraction réussie avec validation Pydantic!\n")
            print(f"📈 Résumé du portfolio:")
            print(f"  - Nombre de positions: {len(portfolio.positions)}")
            print(f"  - Valeur totale: {portfolio.valeur_totale:,.2f}€")
            print(f"  - Date d'évaluation: {portfolio.date_evaluation}")
            print(f"\n📊 Détails des positions:")
            for i, pos in enumerate(portfolio.positions, 1):
                valeur = pos.quantite * pos.prix_achat
                print(f"  {i}. {pos.symbole}: {pos.quantite} actions à {pos.prix_achat}€ = {valeur:,.2f}€")
                print(f"     Acheté le: {pos.date_achat}")
            
            return portfolio
        else:
            # Le modèle a peut-être réussi mais le format n'est pas reconnu
            output = result.output
            print(f"⚠️  Résultat dans output (pas dans data):")
            print(f"Output type: {type(output)}")
            
            # Si c'est déjà un Portfolio (parfois le cas)
            if isinstance(output, Portfolio):
                portfolio = output
                print("✅ Output est un Portfolio valide!\n")
                print(f"📈 Résumé du portfolio:")
                print(f"  - Nombre de positions: {len(portfolio.positions)}")
                print(f"  - Valeur totale: {portfolio.valeur_totale:,.2f}€")
                return portfolio
            else:
                print(f"Output: {str(output)[:300]}...")
                return None
            
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction: {e}")
        print(f"   Type: {type(e).__name__}")
        print("\n💡 Pour un modèle 8B, la validation stricte peut échouer.")
        print("   Essayez sans output_type ou avec des schémas plus simples.")
        return None


if __name__ == "__main__":
    asyncio.run(exemple_extraction_portfolio())

