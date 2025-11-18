# Exemples d'Agentique avec PydanticAI

Ces exemples démontrent différentes capacités agentiques de PydanticAI utilisant le modèle DragonLLM via le Hugging Face Space.

## Installation

```bash
pip install -e ".[dev]"
```

## Exemples

### Agent 1: Extraction de données structurées
**Fichier:** `agent_1_structured_data.py`

Démontre l'extraction et la validation de données financières structurées à partir de textes non structurés.

Fonctionnalités:
- Utilisation de `output_type` avec modèles Pydantic
- Validation automatique des données
- Extraction d'informations complexes (portfolios, transactions)

Exécution:
```bash
python examples/agent_1_structured_data.py
```

### Agent 2: Agent avec outils (Tools)
**Fichier:** `agent_2_tools.py`

Démontre l'utilisation d'outils Python que l'agent peut appeler pour effectuer des calculs financiers précis.

Fonctionnalités:
- Définition d'outils Python (fonctions)
- Appel automatique d'outils par l'agent
- Combinaison de raisonnement LLM + calculs précis
- Utilise numpy-financial pour des calculs testés

Outils disponibles:
- `calculer_valeur_future()` - Intérêts composés
- `calculer_versement_mensuel()` - Prêts immobiliers
- `calculer_performance_portfolio()` - Performance d'investissements
- `calculer_valeur_actuelle()` - Actualisation
- `calculer_taux_interet()` - Calcul de taux requis

Exécution:
```bash
python examples/agent_2_tools.py
```

### Agent 2 Quant: Analyse de risque avancée
**Fichier:** `agent_2_tools_quant.py`

Agent professionnel pour l'analyse quantitative de risque et la gestion d'actifs.

Fonctionnalités:
- Value at Risk (VaR) - Paramétrique, Historique, Monte Carlo
- Analyse de risque de portfolio - Volatilité, corrélation, diversification
- Métriques de performance ajustée du risque - Sharpe, Information Ratio, Beta, Alpha
- Calculs avancés pour professionnels de la gestion d'actifs

Outils disponibles:
- `calculer_var_parametrique()` - VaR méthode variance-covariance
- `calculer_var_historique()` - VaR basée sur données historiques
- `calculer_var_monte_carlo()` - VaR par simulation stochastique
- `calculer_risque_portfolio()` - Analyse complète du risque
- `calculer_metrics_risque_ajuste()` - Performance ajustée du risque

Exécution:
```bash
python examples/agent_2_tools_quant.py
```

Note: Nécessite scipy et pandas. QuantLib-Python est optionnel.

### Agent Option Pricing: Pricing d'options
**Fichier:** `agent_option_pricing.py`

Agent focalisé sur le pricing de call européen et les Greeks via QuantLib.

Fonctionnalités:
- Pricing Black-Scholes analytique
- Calcul Delta / Gamma / Vega / Theta
- Prise en compte du dividende continu

Exécution:
```bash
python examples/agent_option_pricing.py
```

### Agent 2 Compliance: Vérification des tool calls
**Fichier:** `agent_2_compliance.py`

Enveloppe l'agent financier et confirme que des outils ont été appelés pour répondre.

Fonctionnalités:
- Capture du transcript complet
- Vérification des tool calls réels
- Avis “Conforme / Non conforme” pour audit interne

Exécution:
```bash
python examples/agent_2_compliance.py
```

### Agent 3: Workflow multi-étapes
**Fichier:** `agent_3_multi_step.py`

Démontre la création d'un workflow où plusieurs agents spécialisés collaborent.

Fonctionnalités:
- Agents spécialisés (analyse de risque, fiscalité, optimisation)
- Passage de contexte entre agents
- Orchestration de workflows complexes

Exécution:
```bash
python examples/agent_3_multi_step.py
```

### Tests: Vérification des tool calls
**Fichier:** `test_tool_calls_simple.py`

Tests simples pour vérifier que les tool calls fonctionnent correctement.

Exécution:
```bash
python examples/test_tool_calls_simple.py
```

## Points clés démontrés

1. **Extraction structurée**: PydanticAI peut extraire et valider des données complexes
2. **Outils intégrés**: Les agents peuvent appeler des fonctions Python pour des calculs précis
3. **Multi-agents**: Plusieurs agents peuvent collaborer pour résoudre des problèmes complexes
4. **Tool calls**: Le modèle supporte maintenant les tool calls pour exécuter des fonctions Python

## Cas d'usage réels

Ces exemples peuvent être adaptés pour:
- Analyse de documents financiers: Extraction automatique de données de contrats, factures
- Calculs financiers interactifs: Assistants qui calculent en temps réel
- Conseil financier automatisé: Workflows d'analyse multi-domaines
