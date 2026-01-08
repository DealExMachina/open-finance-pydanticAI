#!/usr/bin/env python3
"""
Test script to verify both inference endpoints work correctly.
Runs agent_1 (portfolio extraction) on both Koyeb and HF Space endpoints.
"""

import asyncio
import time
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings

from app.config import ENDPOINTS, settings
from app.models import get_model_for_endpoint


# ============================================================================
# MODELS (from agent_1.py)
# ============================================================================

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


# ============================================================================
# TEST FUNCTION
# ============================================================================

async def test_endpoint(endpoint_name: str) -> dict:
    """Test an endpoint with a simple portfolio extraction task."""
    
    print(f"\n{'='*70}")
    print(f"🧪 Testing endpoint: {endpoint_name.upper()}")
    print(f"{'='*70}")
    
    result = {
        "endpoint": endpoint_name,
        "success": False,
        "time": 0,
        "tokens": 0,
        "error": None,
        "positions_count": 0,
    }
    
    try:
        # Get model for this endpoint
        model = get_model_for_endpoint(endpoint_name)
        endpoint_config = ENDPOINTS.get(endpoint_name, {})
        
        print(f"📍 URL: {endpoint_config.get('url', 'N/A')}")
        print(f"🤖 Model: {endpoint_config.get('model', 'N/A')}")
        
        # Create agent
        agent = Agent(
            model,
            model_settings=ModelSettings(max_output_tokens=600),
            system_prompt="""Expert analyse financière. Extrais données portfolios boursiers.
Règles: Identifie symbole, quantité, prix_achat, date_achat pour chaque position.
CALCUL CRITIQUE: Calculez valeur_totale en additionnant TOUS les produits (quantité × prix_achat) pour chaque position.
Formule: valeur_totale = Σ(quantité × prix_achat) pour toutes les positions.
Répondez avec un objet Portfolio structuré.""",
            output_type=Portfolio,
        )
        
        # Test input
        texte = """
Mon portfolio actuel :
- J'ai acheté 50 actions Airbus (AIR.PA) à 120€ le 15 mars 2024
- 30 actions Sanofi (SAN.PA) à 85€ le 20 février 2024  
- 100 actions TotalEnergies (TTE.PA) à 55€ le 10 janvier 2024

Date d'évaluation : 1er novembre 2024
"""
        
        prompt = (
            f"Extrais les données du portfolio suivant:\n\n{texte}\n\n"
            f"Pour chaque action: symbole, quantite, prix_achat, date_achat (YYYY-MM-DD).\n"
            f"Calcule valeur_totale (somme de quantite × prix_achat).\n"
            f"Utilise la date_evaluation donnée."
        )
        
        print(f"\n📝 Running portfolio extraction...")
        start = time.time()
        response = await agent.run(prompt, output_type=Portfolio)
        elapsed = time.time() - start
        
        portfolio = response.output
        usage = response.usage()
        
        # Calculate expected total
        calculated_total = sum(pos.quantite * pos.prix_achat for pos in portfolio.positions)
        expected_total = 50*120 + 30*85 + 100*55  # 6000 + 2550 + 5500 = 14050
        
        result["success"] = True
        result["time"] = elapsed
        result["tokens"] = usage.total_tokens
        result["positions_count"] = len(portfolio.positions)
        
        print(f"\n✅ SUCCESS!")
        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"📊 Tokens: {usage.total_tokens} (in: {usage.input_tokens}, out: {usage.output_tokens})")
        print(f"⚡ Speed: {usage.total_tokens/elapsed:.1f} tokens/sec")
        print(f"\n📈 Portfolio extracted:")
        print(f"   - Positions: {len(portfolio.positions)}")
        print(f"   - Calculated total: {calculated_total:,.2f}€")
        print(f"   - Model total: {portfolio.valeur_totale:,.2f}€")
        print(f"   - Expected total: {expected_total:,.2f}€")
        
        # Check accuracy
        if len(portfolio.positions) == 3:
            print(f"   ✅ Correct position count (3)")
        else:
            print(f"   ⚠️  Position count: expected 3, got {len(portfolio.positions)}")
            
        if abs(calculated_total - expected_total) < 1:
            print(f"   ✅ Correct total value")
        else:
            print(f"   ⚠️  Total value off by {abs(calculated_total - expected_total):,.2f}€")
        
        # Print positions
        print(f"\n📋 Positions detail:")
        for i, pos in enumerate(portfolio.positions, 1):
            valeur = pos.quantite * pos.prix_achat
            print(f"   {i}. {pos.symbole}: {pos.quantite} × {pos.prix_achat}€ = {valeur:,.2f}€")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    return result


async def main():
    """Test both endpoints."""
    print("="*70)
    print("🚀 OPEN-FINANCE PYDANTIC AI - ENDPOINT REGRESSION TEST")
    print("="*70)
    print(f"Testing both Koyeb and HuggingFace inference servers")
    
    # Test both endpoints
    results = []
    
    for endpoint in ["koyeb", "hf"]:
        try:
            result = await test_endpoint(endpoint)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Critical error testing {endpoint}: {e}")
            results.append({
                "endpoint": endpoint,
                "success": False,
                "error": str(e),
            })
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    all_passed = True
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        time_str = f"{r.get('time', 0):.2f}s" if r.get('time') else "N/A"
        tokens_str = f"{r.get('tokens', 0)} tokens" if r.get('tokens') else "N/A"
        print(f"  {r['endpoint'].upper():10} {status:10} {time_str:10} {tokens_str}")
        if not r["success"]:
            all_passed = False
            if r.get("error"):
                print(f"             Error: {r['error'][:60]}...")
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - No regression detected!")
    else:
        print("❌ SOME TESTS FAILED - Please investigate")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
