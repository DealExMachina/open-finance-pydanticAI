# Open Finance PydanticAI

Application Python utilisant PydanticAI pour créer des agents intelligents spécialisés en finance, connectés au modèle Qwen3-8B-Fin via une API OpenAI-compatible déployée sur Hugging Face Spaces.

## Qu'est-ce que PydanticAI ?

PydanticAI est un framework Python moderne pour construire des applications basées sur des LLM (Large Language Models). Il combine la puissance de Pydantic pour la validation de types et la génération de structures de données avec un système d'agents facile à utiliser.

### Points forts de PydanticAI

**1. Validation de types stricte avec Pydantic**
- Extraction automatique de données structurées depuis les réponses LLM
- Validation des types et des contraintes (min/max, regex, etc.)
- Type safety garantie pour toute la chaîne de traitement

**2. Agents modulaires et extensibles**
- Création d'agents spécialisés en quelques lignes de code
- Intégration native d'outils Python (tools) pour calculs précis
- Système de mémoire conversationnelle intégré

**3. Compatibilité avec tous les modèles**
- Support des APIs OpenAI, Anthropic, et autres
- Architecture flexible pour différents providers de modèles
- Configuration simple via des settings centralisés

**4. Production-ready**
- Gestion automatique des erreurs et retries
- Support des limites d'usage et rate limiting
- Intégration facile avec FastAPI, Django, et autres frameworks

**5. Développement rapide**
- Syntaxe claire et Pythonic
- Documentation automatique via les types
- Débogage facilité avec des messages d'erreur détaillés

## Architecture du projet

Ce projet démontre l'utilisation de PydanticAI pour créer des agents financiers intelligents :

```
open-finance-pydanticAI/
├── app/
│   ├── config.py          # Configuration de l'application
│   ├── models.py          # Configuration du modèle PydanticAI
│   ├── agents.py          # Définition des agents financiers
│   ├── main.py            # API FastAPI
│   └── utils.py           # Utilitaires (parsing, extraction)
├── examples/
│   ├── agent_1_structured_data.py      # Extraction de données structurées
│   ├── agent_2_tools.py                # Agents avec outils Python
│   ├── agent_3_multi_step.py           # Workflows multi-étapes
│   ├── agent_swift.py                  # Génération de messages SWIFT
│   ├── agent_with_tools_and_memory.py  # Outils + mémoire conversationnelle
│   └── memory_strategies.py            # Stratégies de gestion de mémoire
└── docs/
    ├── qwen3_specifications.md         # Spécifications du modèle
    ├── reasoning_models.md             # Gestion des modèles de raisonnement
    └── generation_limits.md            # Limites de génération
```

## Installation

### Prérequis

- Python 3.10+
- Accès à l'espace Hugging Face `jeanbaptdzd/open-finance-llm-8b`

### Installation des dépendances

```bash
# Installer avec pip
pip install -e ".[dev]"

# Ou avec uv (recommandé pour la vitesse)
uv pip install -e ".[dev]"
```

### Variables d'environnement

Créez un fichier `.env` :

```env
HF_SPACE_URL=https://jeanbaptdzd-open-finance-llm-8b.hf.space
API_KEY=not-needed
MODEL_NAME=gpt-3.5-turbo
MAX_TOKENS=1500
TIMEOUT=120
```

## Utilisation

### API FastAPI

Démarrer le serveur :

```bash
uvicorn app.main:app --reload
```

**Endpoints disponibles :**

- `GET /` - Informations sur le service
- `GET /health` - Health check
- `POST /ask` - Poser une question financière

**Exemple de requête :**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Qu'est-ce qu'une date de valeur?"}'
```

### Exemples d'agents

#### Extraction de données structurées

```python
from app.agents import finance_agent

result = await finance_agent.run(
    "Mon portfolio: 50 actions AIR.PA à 120€, 30 actions SAN.PA à 85€"
)
```

#### Agent avec outils de calcul

```python
from examples.agent_with_tools_and_memory import finance_advisor

result = await finance_advisor.run(
    "J'ai 50 000€ à placer à 4% par an pendant 10 ans. Combien aurai-je?"
)
# L'agent utilise automatiquement calculer_valeur_future()
```

#### Conversation avec mémoire

```python
from examples.agent_with_tools_and_memory import ConversationHistory, finance_advisor

history = ConversationHistory()

# Première question
result1 = await finance_advisor.run("J'ai 100 000€ à investir.")
history.add_user_message("J'ai 100 000€ à investir.")
history.add_assistant_message(result1.output)

# Deuxième question avec contexte
context = "\n".join([
    f"{msg['role']}: {msg['content']}"
    for msg in history.get_history_for_agent()
])
result2 = await finance_advisor.run(
    f"Contexte:\n{context}\n\nQuel type d'investissement me recommandes-tu?"
)
```

Voir le répertoire `examples/` pour plus d'exemples détaillés.

## Configuration du modèle

Le projet est configuré pour utiliser le modèle `DragonLLM/qwen3-8b-fin-v1.0` via l'espace Hugging Face qui expose une API compatible OpenAI.

**Caractéristiques du modèle :**
- Spécialisé en terminologie financière française
- Fenêtre de contexte : 32K tokens (base), 128K avec YaRN
- Limite de génération : ~20K tokens (théorique), pratique 2-3K recommandé
- Support du raisonnement avec tags `<think>`

Voir `docs/qwen3_specifications.md` pour plus de détails.

## Exemples disponibles

### 1. Extraction de données structurées (`agent_1_structured_data.py`)
Démontre l'extraction de données financières depuis du texte non structuré.

### 2. Agents avec outils (`agent_2_tools.py`)
Intégration d'outils Python pour calculs financiers précis (intérêts composés, prêts, performance).

### 3. Workflows multi-étapes (`agent_3_multi_step.py`)
Coordination de plusieurs agents spécialisés (analyse de risque, conseil fiscal, optimisation).

### 4. Génération SWIFT (`agent_swift.py`)
Génération et parsing de messages SWIFT bancaires avec validation structurée.

### 5. Outils et mémoire (`agent_with_tools_and_memory.py`)
Combinaison d'outils financiers et de mémoire conversationnelle pour des conseils personnalisés.

### 6. Stratégies de mémoire (`memory_strategies.py`)
Cinq approches différentes pour gérer l'historique des conversations :
- Mémoire simple (tout est conservé)
- Mémoire sélective (faits clés uniquement)
- Mémoire structurée (profil client typé)
- Mémoire avec résumé (compression périodique)
- Mémoire persistante (sauvegarde/chargement multi-session)

## Développement

### Formatage et linting

```bash
# Formatage automatique
black .

# Vérification du style
ruff check .

# Type checking
mypy app
```

### Tests

Les exemples dans `examples/` servent également de tests d'intégration. Exécutez-les pour vérifier que tout fonctionne :

```bash
python examples/agent_1_structured_data.py
python examples/agent_with_tools_and_memory.py
```

## Gestion des modèles de raisonnement

Le modèle Qwen3 utilise des tags `<think>` pour encapsuler son processus de raisonnement. Le projet inclut des utilitaires pour :

- Extraire la réponse finale depuis les tags de raisonnement
- Identifier les termes clés financiers
- Estimer la confiance de la réponse

Voir `app/utils.py` et `docs/reasoning_models.md` pour plus de détails.

## Limitations et bonnes pratiques

**Limites de génération :**
- Recommandé : 1500-2000 tokens pour la plupart des cas
- Maximum pratique : ~3000 tokens selon le contexte
- Le modèle peut terminer prématurément si la limite est trop basse

**Meilleures pratiques :**
- Utiliser des `max_tokens` adaptés à chaque type d'agent
- Implémenter une gestion de mémoire pour les conversations longues
- Valider les réponses structurées avec Pydantic
- Utiliser des outils Python pour les calculs critiques plutôt que de compter sur le LLM

## Documentation technique

- `docs/qwen3_specifications.md` - Spécifications détaillées du modèle Qwen3
- `docs/reasoning_models.md` - Gestion des modèles avec raisonnement
- `docs/generation_limits.md` - Limites de génération et optimisation

## Licence

Ce projet est fourni à des fins éducatives et de démonstration.

## Contribution

Les contributions sont les bienvenues. Veuillez suivre les conventions de code existantes et inclure des tests pour les nouvelles fonctionnalités.
