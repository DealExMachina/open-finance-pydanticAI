"""
Agent avec outils financiers et mémoire (history)

Cet exemple démontre:
1. Utilisation d'outils Python pour calculs financiers
2. Mémoire/conversation history pour maintenir le contexte
3. Agents qui se souviennent des calculs précédents
"""

import asyncio
from typing import Annotated, List
from pydantic import BaseModel
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# Simple History wrapper for managing conversation
class ConversationHistory:
    """Gère l'historique de conversation pour les agents."""
    
    def __init__(self):
        self.messages: List[dict] = []
    
    def add_user_message(self, content: str):
        """Ajoute un message utilisateur."""
        # Pour simplifier, on crée une structure simple
        # En production, utiliser les types corrects de PydanticAI
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        """Ajoute un message assistant."""
        self.messages.append({"role": "assistant", "content": content})
    
    def get_history_for_agent(self) -> List[dict]:
        """Retourne l'historique au format pour l'agent."""
        return self.messages
    
    def __len__(self):
        return len(self.messages)

# ============================================================================
# OUTILS FINANCIERS
# ============================================================================

def calculer_valeur_future(
    capital_initial: float,
    taux_annuel: float,
    duree_annees: float
) -> str:
    """Calcule la valeur future avec intérêts composés.
    
    Args:
        capital_initial: Montant initial en euros
        taux_annuel: Taux d'intérêt annuel (ex: 0.04 pour 4%)
        duree_annees: Durée en années
    
    Returns:
        Résultat formaté du calcul
    """
    valeur_future = capital_initial * (1 + taux_annuel) ** duree_annees
    interets = valeur_future - capital_initial
    rendement_pct = (interets / capital_initial) * 100
    
    return (
        f"💰 Valeur future: {valeur_future:,.2f}€\n"
        f"   Capital initial: {capital_initial:,.2f}€\n"
        f"   Intérêts générés: {interets:,.2f}€ ({rendement_pct:.2f}%)\n"
        f"   Durée: {duree_annees} ans à {taux_annuel*100:.2f}% par an"
    )


def calculer_versement_mensuel(
    capital_emprunte: float,
    taux_annuel: float,
    duree_annees: int
) -> str:
    """Calcule le versement mensuel pour un prêt immobilier.
    
    Args:
        capital_emprunte: Montant emprunté en euros
        taux_annuel: Taux d'intérêt annuel (ex: 0.035 pour 3.5%)
        duree_annees: Durée du prêt en années
    
    Returns:
        Résultat formaté du calcul
    """
    duree_mois = duree_annees * 12
    taux_mensuel = taux_annuel / 12
    versement = capital_emprunte * (
        taux_mensuel * (1 + taux_mensuel) ** duree_mois
    ) / ((1 + taux_mensuel) ** duree_mois - 1)
    
    total_rembourse = versement * duree_mois
    cout_total = total_rembourse - capital_emprunte
    
    return (
        f"🏠 Versement mensuel: {versement:,.2f}€\n"
        f"   Capital emprunté: {capital_emprunte:,.2f}€\n"
        f"   Total remboursé: {total_rembourse:,.2f}€\n"
        f"   Coût du crédit: {cout_total:,.2f}€\n"
        f"   Durée: {duree_annees} ans ({duree_mois} mois) à {taux_annuel*100:.2f}%"
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
        Résultat formaté du calcul
    """
    gain_absolu = valeur_actuelle - valeur_initiale
    gain_pourcentage = (gain_absolu / valeur_initiale) * 100
    rendement_annuelise = ((valeur_actuelle / valeur_initiale) ** (365 / duree_jours) - 1) * 100
    
    return (
        f"📈 Performance portfolio:\n"
        f"   Gain absolu: {gain_absolu:+,.2f}€ ({gain_pourcentage:+.2f}%)\n"
        f"   Rendement annualisé: {rendement_annuelise:+.2f}%\n"
        f"   Durée: {duree_jours} jours"
    )


def calculer_ratio_dette(
    dette_totale: float,
    revenus_annuels: float
) -> str:
    """Calcule le ratio d'endettement.
    
    Args:
        dette_totale: Dette totale en euros
        revenus_annuels: Revenus annuels en euros
    
    Returns:
        Résultat formaté du calcul
    """
    ratio = (dette_totale / revenus_annuels) * 100
    annees_remboursement = dette_totale / revenus_annuels
    
    return (
        f"💳 Ratio d'endettement:\n"
        f"   Ratio: {ratio:.2f}% des revenus annuels\n"
        f"   Dette totale: {dette_totale:,.2f}€\n"
        f"   Revenus annuels: {revenus_annuels:,.2f}€\n"
        f"   Années de remboursement: {annees_remboursement:.2f} ans"
    )


# ============================================================================
# AGENT AVEC OUTILS ET MÉMOIRE
# ============================================================================

finance_advisor = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),
    system_prompt=(
        "Vous êtes un conseiller financier expert qui aide les clients à prendre "
        "des décisions financières éclairées. Vous avez accès à des outils de calcul "
        "financier précis.\n\n"
        "Utilisez les outils disponibles pour:\n"
        "- Calculer les valeurs futures d'investissements\n"
        "- Calculer les versements de prêts immobiliers\n"
        "- Analyser la performance de portfolios\n"
        "- Évaluer les ratios d'endettement\n\n"
        "Gardez en mémoire les informations précédentes de la conversation pour "
        "fournir des conseils cohérents et personnalisés.\n\n"
        "Répondez toujours en français de manière claire et structurée."
    ),
    tools=[
        calculer_valeur_future,
        calculer_versement_mensuel,
        calculer_performance_portfolio,
        calculer_ratio_dette,
    ],
)


# ============================================================================
# EXEMPLES D'UTILISATION
# ============================================================================

async def exemple_conversation_avec_memoire():
    """Exemple de conversation avec mémoire (history)."""
    print("💬 Exemple: Conversation avec mémoire et outils")
    print("=" * 60)
    
    # Créer une histoire de conversation vide
    history = ConversationHistory()
    
    # Question 1: Calcul initial
    print("\n👤 Client: 'J'ai 50 000€ à placer à 4% par an pendant 10 ans. Combien aurai-je?'")
    prompt1 = "J'ai 50 000€ à placer à 4% par an pendant 10 ans. Combien aurai-je?"
    result1 = await finance_advisor.run(prompt1)
    history.add_user_message(prompt1)
    history.add_assistant_message(result1.output)
    print(f"\n🤖 Conseiller:\n{result1.output[:400]}...")
    
    # Question 2: Référence au calcul précédent (mémoire via contexte)
    print("\n" + "-" * 60)
    print("\n👤 Client: 'Et si j'augmente à 5%?'")
    # Inclure le contexte précédent dans le prompt
    context = "\n".join([
        f"{'👤' if msg['role'] == 'user' else '🤖'} {msg['content'][:200]}..."
        for msg in history.get_history_for_agent()
    ])
    prompt2 = f"Contexte précédent:\n{context}\n\nNouvelle question: Et si j'augmente le taux à 5%?"
    result2 = await finance_advisor.run(prompt2)
    history.add_user_message("Et si j'augmente le taux à 5%?")
    history.add_assistant_message(result2.output)
    print(f"\n🤖 Conseiller:\n{result2.output[:400]}...")
    
    # Question 3: Nouvelle question avec contexte
    print("\n" + "-" * 60)
    print("\n👤 Client: 'En fait, je veux plutôt emprunter 200 000€ sur 20 ans à 3.5% pour un achat immobilier'")
    context = "\n".join([
        f"{msg['role']}: {msg['content'][:150]}..."
        for msg in history.get_history_for_agent()[-4:]  # Derniers 4 messages
    ])
    prompt3 = f"Contexte:\n{context}\n\nEn fait, je veux plutôt emprunter 200 000€ sur 20 ans à 3.5% pour un achat immobilier. Combien paierai-je par mois?"
    result3 = await finance_advisor.run(prompt3)
    history.add_user_message("En fait, je veux plutôt emprunter 200 000€ sur 20 ans à 3.5%")
    history.add_assistant_message(result3.output)
    print(f"\n🤖 Conseiller:\n{result3.output[:400]}...")
    
    # Afficher l'historique complet
    print("\n" + "=" * 60)
    print("📚 Historique de la conversation:")
    print("=" * 60)
    for i, msg in enumerate(history.get_history_for_agent(), 1):
        role = msg['role']
        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        print(f"{i}. {role.upper()}: {content}")


async def exemple_portfolio_avec_memoire():
    """Exemple d'analyse de portfolio avec mémoire des calculs précédents."""
    print("\n\n📊 Exemple: Analyse de portfolio avec mémoire")
    print("=" * 60)
    
    history = ConversationHistory()
    
    # Initialisation du portfolio
    print("\n👤 Client: 'Mon portfolio valait 100 000€ il y a 6 mois, aujourd'hui il vaut 115 000€'")
    prompt1 = "Mon portfolio valait 100 000€ il y a 6 mois, aujourd'hui il vaut 115 000€. Calcule la performance."
    result1 = await finance_advisor.run(prompt1)
    history.add_user_message(prompt1)
    history.add_assistant_message(result1.output)
    print(f"\n🤖 Conseiller:\n{result1.output}")
    
    # Suivi avec mémoire
    print("\n" + "-" * 60)
    print("\n👤 Client: 'Et si je projette cette performance sur 5 ans?'")
    context = f"Contexte précédent:\n{result1.output[:300]}...\n\n"
    prompt2 = context + "Et si je projette cette performance annuelle sur 5 ans avec mon capital actuel de 115 000€?"
    result2 = await finance_advisor.run(prompt2)
    history.add_user_message("Et si je projette cette performance sur 5 ans?")
    history.add_assistant_message(result2.output)
    print(f"\n🤖 Conseiller:\n{result2.output[:500]}...")
    
    return history


async def exemple_analyse_complete_avec_memoire():
    """Exemple complet d'analyse financière avec outils et mémoire."""
    print("\n\n🎯 Exemple: Analyse financière complète avec mémoire")
    print("=" * 60)
    
    history = ConversationHistory()
    
    questions = [
        "Je gagne 80 000€ par an et j'ai une dette de 200 000€. Quel est mon ratio d'endettement?",
        "Je veux emprunter 300 000€ pour une résidence principale à 3.5% sur 25 ans. Combien paierai-je?",
        "Si j'investis les 74 000€ restants après le prêt à 5% par an pendant 15 ans, combien aurai-je?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}: {question}")
        print("=" * 60)
        
        # Inclure le contexte si ce n'est pas la première question
        if i > 1:
            context = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}..."
                for msg in history.get_history_for_agent()[-2:]  # 2 derniers messages
            ])
            full_question = f"Contexte:\n{context}\n\n{question}"
        else:
            full_question = question
        
        result = await finance_advisor.run(full_question)
        history.add_user_message(question)
        history.add_assistant_message(result.output)
        print(f"\nRéponse:\n{result.output[:600]}...")
        
        # Petit délai pour éviter les timeouts
        await asyncio.sleep(1)
    
    print("\n" + "=" * 60)
    print("✅ Analyse complète terminée!")
    print(f"📊 Total de messages dans l'historique: {len(history)}")


async def exemple_extraction_memoire():
    """Montre comment extraire des informations de la mémoire."""
    print("\n\n🔍 Exemple: Extraction d'informations de la mémoire")
    print("=" * 60)
    
    history = ConversationHistory()
    
    # Conversation initiale
    prompt1 = "J'ai un capital de 100 000€ à placer à 4% pendant 10 ans."
    result1 = await finance_advisor.run(prompt1)
    history.add_user_message(prompt1)
    history.add_assistant_message(result1.output)
    
    prompt2 = "Je gagne 75 000€ par an et j'ai une dette de 180 000€."
    result2 = await finance_advisor.run(prompt2)
    history.add_user_message(prompt2)
    history.add_assistant_message(result2.output)
    
    # Question qui utilise la mémoire
    print("\n👤 Client: 'Résume ma situation financière'")
    context = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in history.get_history_for_agent()
    ])
    result = await finance_advisor.run(
        f"Contexte de la conversation:\n{context}\n\n"
        "Peux-tu résumer ma situation financière actuelle basée sur ce que je t'ai dit?"
    )
    
    print(f"\n🤖 Conseiller:\n{result.output}")
    
    # Afficher l'historique
    print("\n" + "-" * 60)
    print("📚 Messages dans l'historique:")
    for msg in history.get_history_for_agent():
        print(f"  {msg['role']}: {msg['content'][:150]}...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AGENTS AVEC OUTILS FINANCIERS ET MÉMOIRE")
    print("=" * 60)
    
    # Exemple 1: Conversation avec mémoire
    asyncio.run(exemple_conversation_avec_memoire())
    
    # Exemple 2: Portfolio avec mémoire
    asyncio.run(exemple_portfolio_avec_memoire())
    
    # Exemple 3: Extraction de mémoire
    asyncio.run(exemple_extraction_memoire())
    
    print("\n\n" + "=" * 60)
    print("✅ Tous les exemples terminés!")
    print("=" * 60)

