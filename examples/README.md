# Exemples d'Agentique avec PydanticAI

Ces exemples démontrent différentes capacités agentiques de PydanticAI utilisant le modèle DragonLLM via le Hugging Face Space.

## Installation

```bash
cd /Users/jeanbapt/open-finance-pydanticAI
pip install -e ".[dev]"
```

## Exemples

### Agent 1: Extraction de données structurées
**Fichier:** `agent_1_structured_data.py`

Démontre l'extraction et la validation de données financières structurées à partir de textes non structurés.

**Fonctionnalités:**
- Utilisation de `output_type` avec modèles Pydantic
- Validation automatique des données
- Extraction d'informations complexes (portfolios, transactions)

**Exécution:**
```bash
python examples/agent_1_structured_data.py
```

### Agent 2: Agent avec outils (Tools)
**Fichier:** `agent_2_tools.py`

Démontre l'utilisation d'outils Python que l'agent peut appeler pour effectuer des calculs.

**Fonctionnalités:**
- Définition d'outils Python (fonctions)
- Appel automatique d'outils par l'agent
- Combinaison de raisonnement LLM + calculs précis

**Outils disponibles:**
- `calculer_valeur_future()` - Intérêts composés
- `calculer_versement_mensuel()` - Prêts immobiliers
- `calculer_performance_portfolio()` - Performance d'investissements

**Exécution:**
```bash
python examples/agent_2_tools.py
```

### Agent 4: Outils et mémoire
**Fichier:** `agent_with_tools_and_memory.py`

Démontre l'utilisation combinée d'outils Python et de mémoire (History) pour créer des agents conversationnels intelligents.

**Fonctionnalités:**
- Outils financiers intégrés (calculs précis)
- Mémoire conversationnelle (History)
- Agents qui se souviennent du contexte
- Conseils personnalisés basés sur l'historique

**Outils disponibles:**
- `calculer_valeur_future()` - Intérêts composés
- `calculer_versement_mensuel()` - Prêts immobiliers
- `calculer_performance_portfolio()` - Performance d'investissements
- `calculer_ratio_dette()` - Analyse d'endettement

**Exécution:**
```bash
python examples/agent_with_tools_and_memory.py
```

### Agent 5: Stratégies de mémoire
**Fichier:** `memory_strategies.py`

Démontre différentes stratégies de gestion de mémoire pour optimiser les performances et la persistance.

**Stratégies:**
1. Mémoire simple (History) - Tout est conservé
2. Mémoire sélective - Extraction de faits clés
3. Mémoire structurée - Profil client typé
4. Mémoire avec résumé - Compression périodique
5. Mémoire persistante - Sauvegarde/chargement multi-session

**Exécution:**
```bash
python examples/memory_strategies.py
```

### Agent 3: Workflow multi-étapes
**Fichier:** `agent_3_multi_step.py`

Démontre la création d'un workflow où plusieurs agents spécialisés collaborent.

**Fonctionnalités:**
- Agents spécialisés (analyse de risque, fiscalité, optimisation)
- Passage de contexte entre agents
- Orchestration de workflows complexes

**Agents:**
- `risk_analyst` - Analyse de risque financier
- `tax_advisor` - Conseil fiscal français
- `portfolio_optimizer` - Optimisation de portfolio

**Exécution:**
```bash
python examples/agent_3_multi_step.py
```

## Points clés démontrés

1. **Extraction structurée**: PydanticAI peut extraire et valider des données complexes
2. **Outils intégrés**: Les agents peuvent appeler des fonctions Python pour des calculs précis
3. **Multi-agents**: Plusieurs agents peuvent collaborer pour résoudre des problèmes complexes
4. **Raisonnement**: Le modèle Qwen3 fournit le raisonnement via les balises `<think>`

## Cas d'usage réels

Ces exemples peuvent être adaptés pour:
- **Analyse de documents financiers**: Extraction automatique de données de contrats, factures
- **Calculs financiers interactifs**: Assistants qui calculent en temps réel
- **Conseil financier automatisé**: Workflows d'analyse multi-domaines

