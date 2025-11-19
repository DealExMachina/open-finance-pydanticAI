"""
Test simplifié pour modèle 8B: Évaluation JSON avec schémas adaptés

Ce test utilise des schémas simples et des prompts optimisés pour
évaluer les capacités réelles d'un petit modèle (8B paramètres).
"""

import asyncio
from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# ============================================================================
# MODÈLES SIMPLES ADAPTÉS POUR MODÈLE 8B
# ============================================================================

class Position(BaseModel):
    """Position boursière simple."""
    symbole: str = Field(description="Code de l'action (ex: AIR.PA)")
    quantite: int = Field(description="Nombre d'actions", ge=0)
    prix: float = Field(description="Prix unitaire en euros", ge=0)


class PortfolioSimple(BaseModel):
    """Portfolio simplifié."""
    positions: List[Position] = Field(description="Liste des positions")
    total: float = Field(description="Valeur totale en euros", ge=0)


# ============================================================================
# AGENT AVEC PROMPT OPTIMISÉ
# ============================================================================

extract_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=800),
    system_prompt=(
        "Tu es un assistant financier. Tu extrais des données de portfolios en JSON.\n\n"
        "RÈGLES:\n"
        "1. Lis le texte attentivement\n"
        "2. Identifie chaque action: symbole, quantite, prix\n"
        "3. Calcule le total: somme de (quantite × prix)\n"
        "4. Réponds UNIQUEMENT en JSON, sans texte avant ou après\n\n"
        "EXEMPLE:\n"
        'Texte: "10 AIR.PA à 120€ et 5 SAN.PA à 80€"\n'
        'JSON: {"positions": [{"symbole": "AIR.PA", "quantite": 10, "prix": 120.0}, '
        '{"symbole": "SAN.PA", "quantite": 5, "prix": 80.0}], "total": 1600.0}\n\n'
        "IMPORTANT: Commence par { et termine par }, pas de texte autour!"
    ),
)


# ============================================================================
# TESTS SIMPLIFIÉS
# ============================================================================

TEST_CASES = [
    {
        "num": 1,
        "name": "Une seule position",
        "texte": "J'ai 10 actions Airbus (AIR.PA) à 120€",
        "expected_positions": 1,
        "expected_total_approx": 1200.0,
    },
    {
        "num": 2,
        "name": "Deux positions",
        "texte": "Portfolio: 20 AIR.PA à 100€ et 30 SAN.PA à 50€",
        "expected_positions": 2,
        "expected_total_approx": 3500.0,
    },
    {
        "num": 3,
        "name": "Trois positions",
        "texte": (
            "Mon portfolio:\n"
            "- 15 actions Airbus (AIR.PA) achetées à 110€\n"
            "- 25 actions Sanofi (SAN.PA) à 85€\n"
            "- 10 actions Total (TTE.PA) à 55€"
        ),
        "expected_positions": 3,
        "expected_total_approx": 4450.0,
    },
]


async def run_test(test_case: dict) -> dict:
    """Exécute un test et retourne les résultats."""
    print(f"\n{'='*70}")
    print(f"TEST {test_case['num']}: {test_case['name']}")
    print(f"{'='*70}")
    print(f"Texte: {test_case['texte'][:80]}...")
    
    result = {
        "num": test_case["num"],
        "name": test_case["name"],
        "success": False,
        "has_data": False,
        "errors": [],
    }
    
    try:
        # Prompt simple et clair
        prompt = (
            f"Extrais les données du portfolio suivant en JSON:\n\n"
            f"{test_case['texte']}\n\n"
            f"Fournis: positions (symbole, quantite, prix) et total."
        )
        
        # Exécution avec output_type
        agent_result = await extract_agent.run(prompt, output_type=PortfolioSimple)
        
        # Récupérer le portfolio - peut être dans data ou output
        portfolio = None
        try:
            portfolio = agent_result.data
        except AttributeError:
            # Pas de .data, essayer .output
            if isinstance(agent_result.output, PortfolioSimple):
                portfolio = agent_result.output
        
        # Vérification du résultat
        if portfolio:
            result["has_data"] = True
            result["nb_positions"] = len(portfolio.positions)
            result["total"] = portfolio.total
            
            # Validation
            expected_pos = test_case["expected_positions"]
            expected_total = test_case["expected_total_approx"]
            
            pos_ok = len(portfolio.positions) == expected_pos
            total_ok = abs(portfolio.total - expected_total) < expected_total * 0.1  # 10% tolérance
            
            if pos_ok and total_ok:
                result["success"] = True
                print(f"✅ SUCCÈS!")
                print(f"   Positions: {len(portfolio.positions)}")
                print(f"   Total: {portfolio.total:,.2f}€")
            else:
                if not pos_ok:
                    result["errors"].append(
                        f"Nombre de positions: attendu {expected_pos}, obtenu {len(portfolio.positions)}"
                    )
                if not total_ok:
                    result["errors"].append(
                        f"Total: attendu ~{expected_total:.2f}€, obtenu {portfolio.total:.2f}€"
                    )
                print(f"⚠️  PARTIELLEMENT RÉUSSI")
                for err in result["errors"]:
                    print(f"   - {err}")
        else:
            result["errors"].append("Pas de données validées (result.data manquant)")
            print(f"❌ ÉCHEC: {result['errors'][0]}")
            
            # Montrer ce que le modèle a réellement généré
            output = agent_result.output
            if isinstance(output, (PortfolioSimple, Position)):
                print(f"   ⚠️  Output est un objet Pydantic (pas JSON): {type(output)}")
                print(f"   Le modèle a réussi mais le format est incorrect!")
                result["model_output_type"] = str(type(output))
            else:
                print(f"   Output brut ({type(output).__name__}): {str(output)[:200]}...")
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:200]
        result["errors"].append(f"{error_type}: {error_msg}")
        print(f"❌ ERREUR {error_type}: {error_msg}")
        
        # Diagnostic selon le type d'erreur
        if "ToolRetryError" in error_type or "UnexpectedModelBehavior" in error_type:
            print(f"   💡 Le modèle ne génère pas du JSON valide après plusieurs tentatives")
            print(f"   📝 Ceci est une LIMITATION DU MODÈLE 8B, pas un bug du code")
        elif "ValidationError" in error_type:
            print(f"   💡 Le JSON généré ne correspond pas au schéma Pydantic")
        else:
            print(f"   💡 Erreur inattendue - vérifier la connexion au modèle")
    
    return result


async def run_all_tests():
    """Exécute tous les tests et affiche un résumé."""
    print("="*70)
    print("TESTS SIMPLIFIÉS POUR MODÈLE 8B")
    print("="*70)
    print("Objectif: Évaluer les capacités JSON d'un petit modèle")
    print()
    
    results = []
    for test_case in TEST_CASES:
        result = await run_test(test_case)
        results.append(result)
        await asyncio.sleep(0.5)  # Pause entre tests
    
    # Résumé
    print(f"\n{'='*70}")
    print("RÉSUMÉ")
    print(f"{'='*70}")
    
    successes = sum(1 for r in results if r["success"])
    partial = sum(1 for r in results if r["has_data"] and not r["success"])
    failures = sum(1 for r in results if not r["has_data"])
    total = len(results)
    
    print(f"\n✅ Succès complets: {successes}/{total} ({successes/total*100:.0f}%)")
    print(f"⚠️  Succès partiels: {partial}/{total} ({partial/total*100:.0f}%)")
    print(f"❌ Échecs: {failures}/{total} ({failures/total*100:.0f}%)")
    
    if successes == total:
        print("\n🎉 EXCELLENT! Le modèle gère bien les JSON simples!")
    elif successes + partial >= total * 0.7:
        print("\n👍 BON! Le modèle a des capacités JSON raisonnables")
    elif successes + partial >= total * 0.5:
        print("\n⚠️  MOYEN: Le modèle a des difficultés avec le JSON structuré")
    else:
        print("\n❌ FAIBLE: Le modèle n'est pas adapté pour du JSON strict")
    
    print("\n💡 Pour améliorer:")
    if failures > 0:
        print("  - Vérifier que le modèle reçoit les bons exemples")
        print("  - Simplifier encore les schémas")
        print("  - Utiliser des prompts encore plus explicites")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())

