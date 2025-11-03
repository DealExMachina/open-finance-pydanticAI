"""
Stratégies de gestion de mémoire pour agents financiers

Démontre différentes approches pour gérer la mémoire et l'historique
des conversations avec PydanticAI.
"""

import asyncio
from typing import List
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model


# Simple History wrapper
class ConversationHistory:
    """Gère l'historique de conversation pour les agents."""
    
    def __init__(self):
        self.messages: List[dict] = []
    
    def add_user_message(self, content: str):
        """Ajoute un message utilisateur."""
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        """Ajoute un message assistant."""
        self.messages.append({"role": "assistant", "content": content})
    
    def get_history_for_agent(self) -> List[dict]:
        """Retourne l'historique au format pour l'agent."""
        return self.messages
    
    def all_messages(self):
        """Itérateur sur tous les messages."""
        return iter(self.messages)
    
    def __len__(self):
        return len(self.messages)


# ============================================================================
# AGENT FINANCIER DE BASE
# ============================================================================

finance_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1500),
    system_prompt=(
        "Vous êtes un conseiller financier expert. "
        "Vous gardez en mémoire les informations précédentes de la conversation "
        "pour fournir des conseils cohérents et personnalisés. "
        "Répondez toujours en français."
    ),
)


# ============================================================================
# STRATÉGIE 1: MÉMOIRE SIMPLE (HISTORY)
# ============================================================================

async def strategie_memoire_simple():
    """Mémoire basique avec History - tout est conservé."""
    print("📝 Stratégie 1: Mémoire simple (tout est conservé)")
    print("=" * 60)
    
    history = ConversationHistory()
    
    # Conversation
    result1 = await finance_agent.run("J'ai 100 000€ à investir.")
    history.add_user_message("J'ai 100 000€ à investir.")
    history.add_assistant_message(result1.output)
    
    result2 = await finance_agent.run("Mon objectif est la retraite dans 20 ans.")
    history.add_user_message("Mon objectif est la retraite dans 20 ans.")
    history.add_assistant_message(result2.output)
    
    # Question qui nécessite la mémoire
    context = "\n".join([f"{msg['role']}: {msg['content'][:200]}" for msg in history.get_history_for_agent()])
    result = await finance_agent.run(
        f"Contexte:\n{context}\n\nQuel type d'investissement me recommandes-tu?"
    )
    
    print(f"\nRéponse:\n{result.output[:400]}...")
    print(f"\n📊 Messages dans l'historique: {len(history)}")


# ============================================================================
# STRATÉGIE 2: MÉMOIRE SÉLECTIVE (FILTRAGE)
# ============================================================================

class SelectiveMemory:
    """Mémoire sélective qui ne garde que les informations importantes."""
    
    def __init__(self):
        self.history = History()
        self.important_facts = []
    
    def add_fact(self, fact: str):
        """Ajoute un fait important à retenir."""
        self.important_facts.append(fact)
    
    def get_context(self) -> str:
        """Retourne le contexte des faits importants."""
        if not self.important_facts:
            return ""
        return "Faits importants à retenir:\n" + "\n".join(f"- {f}" for f in self.important_facts)


async def strategie_memoire_selective():
    """Mémoire sélective - on garde seulement les faits clés."""
    print("\n\n🎯 Stratégie 2: Mémoire sélective (faits clés)")
    print("=" * 60)
    
    memory = SelectiveMemory()
    history = ConversationHistory()
    
    # Conversation avec extraction de faits
    prompt = "J'ai 100 000€ à investir pour la retraite dans 20 ans. J'ai 45 ans."
    result1 = await finance_agent.run(prompt)
    history.add_user_message(prompt)
    history.add_assistant_message(result1.output)
    memory.add_fact("Capital: 100 000€")
    memory.add_fact("Objectif: Retraite")
    memory.add_fact("Horizon: 20 ans")
    memory.add_fact("Âge: 45 ans")
    
    print(f"\n📌 Faits extraits: {memory.important_facts}")
    
    # Nouvelle question avec contexte des faits
    context = memory.get_context()
    result2 = await finance_agent.run(
        f"{context}\n\nQuestion: Quel type d'investissement me recommandes-tu?"
    )
    
    print(f"\nRéponse:\n{result2.output[:400]}...")


# ============================================================================
# STRATÉGIE 3: MÉMOIRE STRUCTURÉE (PROFIL CLIENT)
# ============================================================================

class ClientProfile:
    """Profil structuré du client."""
    
    def __init__(self):
        self.age: int | None = None
        self.revenus_annuels: float | None = None
        self.capital: float | None = None
        self.objectifs: list[str] = []
        self.horizon: int | None = None
        self.profil_risque: str | None = None
    
    def to_context(self) -> str:
        """Convertit le profil en contexte pour l'agent."""
        parts = ["Profil client:"]
        if self.age:
            parts.append(f"- Âge: {self.age} ans")
        if self.revenus_annuels:
            parts.append(f"- Revenus annuels: {self.revenus_annuels:,.0f}€")
        if self.capital:
            parts.append(f"- Capital: {self.capital:,.0f}€")
        if self.objectifs:
            parts.append(f"- Objectifs: {', '.join(self.objectifs)}")
        if self.horizon:
            parts.append(f"- Horizon: {self.horizon} ans")
        if self.profil_risque:
            parts.append(f"- Profil de risque: {self.profil_risque}")
        return "\n".join(parts)


async def strategie_memoire_structuree():
    """Mémoire structurée avec profil client."""
    print("\n\n📋 Stratégie 3: Mémoire structurée (profil client)")
    print("=" * 60)
    
    profile = ClientProfile()
    history = ConversationHistory()
    
    # Construction du profil
    prompt = "J'ai 45 ans, je gagne 80 000€ par an et j'ai 150 000€ d'épargne. Je veux préparer ma retraite dans 20 ans avec un profil modéré."
    result1 = await finance_agent.run(prompt)
    history.add_user_message(prompt)
    history.add_assistant_message(result1.output)
    
    # Extraction structurée (ici simplifiée, idéalement avec output_type)
    profile.age = 45
    profile.revenus_annuels = 80000
    profile.capital = 150000
    profile.objectifs = ["Retraite"]
    profile.horizon = 20
    profile.profil_risque = "Modéré"
    
    print(f"\n📋 Profil client construit:\n{profile.to_context()}")
    
    # Utilisation du profil dans les conseils
    context = profile.to_context()
    result2 = await finance_agent.run(
        f"{context}\n\nQuelle stratégie d'investissement me recommandes-tu?"
    )
    
    print(f"\nRéponse:\n{result2.output[:500]}...")


# ============================================================================
# STRATÉGIE 4: MÉMOIRE AVEC RÉSUMÉ (COMPRESSION)
# ============================================================================

async def strategie_memoire_avec_resume():
    """Mémoire avec résumé périodique pour éviter la surcharge."""
    print("\n\n📄 Stratégie 4: Mémoire avec résumé (compression)")
    print("=" * 60)
    
    history = ConversationHistory()
    
    # Conversation longue
    messages = [
        "J'ai 45 ans et je gagne 80 000€ par an.",
        "J'ai 150 000€ d'épargne actuellement.",
        "Mon objectif est la retraite dans 20 ans.",
        "J'ai un profil de risque modéré.",
        "Je préfère les investissements diversifiés.",
    ]
    
    for msg in messages:
        result = await finance_agent.run(msg)
        history.add_user_message(msg)
        history.add_assistant_message(result.output)
        print(f"  ✓ Ajouté: {msg}")
    
    # Créer un résumé quand l'historique devient long
    if len(history) > 6:
        print("\n📝 Création d'un résumé de conversation...")
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history.get_history_for_agent()])
        summary_result = await finance_agent.run(
            f"Contexte:\n{context}\n\n"
            "Résume en 3-4 phrases les informations clés que le client t'a données "
            "dans cette conversation pour créer un profil client."
        )
        print(f"\n📄 Résumé:\n{summary_result.output[:300]}...")
        
        # Utiliser le résumé comme nouveau contexte
        summary_context = summary_result.output
        result = await finance_agent.run(
            f"Contexte client:\n{summary_context}\n\n"
            "Quelle stratégie d'investissement recommandes-tu?"
        )
        print(f"\n💡 Recommandation basée sur le résumé:\n{result.output[:400]}...")


# ============================================================================
# STRATÉGIE 5: MÉMOIRE MULTI-SESSION (PERSISTANCE)
# ============================================================================

import json
from datetime import datetime


class PersistentMemory:
    """Mémoire persistante qui peut être sauvegardée/chargée."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.history = History()
        self.facts = {}
        self.last_interaction = None
    
    def save(self, filepath: str):
        """Sauvegarde la mémoire dans un fichier."""
        data = {
            "client_id": self.client_id,
            "facts": self.facts,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in self.history.all_messages()
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str):
        """Charge la mémoire depuis un fichier."""
        with open(filepath, "r") as f:
            data = json.load(f)
        
        memory = cls(data["client_id"])
        memory.facts = data.get("facts", {})
        if data.get("last_interaction"):
            memory.last_interaction = datetime.fromisoformat(data["last_interaction"])
        
        # Reconstruire l'historique (simplifié)
        for msg_data in data.get("messages", []):
            # Note: Cette reconstruction est simplifiée
            # En production, utilisez l'API History correctement
            pass
        
        return memory


async def strategie_memoire_persistante():
    """Mémoire persistante entre sessions."""
    print("\n\n💾 Stratégie 5: Mémoire persistante (multi-session)")
    print("=" * 60)
    
    # Session 1
    memory = PersistentMemory("client_001")
    memory.facts = {
        "age": 45,
        "revenus": 80000,
        "capital": 150000,
        "objectif": "Retraite",
    }
    memory.last_interaction = datetime.now()
    
    # Sauvegarder
    filepath = "/tmp/client_memory.json"
    memory.save(filepath)
    print(f"✅ Mémoire sauvegardée: {filepath}")
    
    # Simuler une nouvelle session (chargement)
    print("\n🔄 Nouvelle session - Chargement de la mémoire...")
    loaded_memory = PersistentMemory.load(filepath)
    
    print(f"📋 Faits chargés: {loaded_memory.facts}")
    print(f"🕐 Dernière interaction: {loaded_memory.last_interaction}")
    
    # Utiliser la mémoire chargée
    context = "Contexte client:\n" + "\n".join(
        f"- {k}: {v}" for k, v in loaded_memory.facts.items()
    )
    
    result = await finance_agent.run(
        f"{context}\n\nJe reviens vous voir 6 mois plus tard. Mon capital est maintenant de 160 000€. "
        "Quelle est ma nouvelle situation?"
    )
    
    print(f"\nRéponse:\n{result.output[:400]}...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STRATÉGIES DE GESTION DE MÉMOIRE POUR AGENTS")
    print("=" * 60)
    
    # Stratégie 1
    asyncio.run(strategie_memoire_simple())
    
    # Stratégie 2
    asyncio.run(strategie_memoire_selective())
    
    # Stratégie 3
    asyncio.run(strategie_memoire_structuree())
    
    # Stratégie 4
    asyncio.run(strategie_memoire_avec_resume())
    
    # Stratégie 5
    asyncio.run(strategie_memoire_persistante())
    
    print("\n\n" + "=" * 60)
    print("✅ Toutes les stratégies démontrées!")
    print("=" * 60)

