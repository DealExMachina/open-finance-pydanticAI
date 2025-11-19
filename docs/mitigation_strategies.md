# Stratégies de Mitigation pour Modèles Fine-Tunés (Qwen 8B)

Ce document décrit les stratégies de mitigation pour éviter les échecs courants avec les modèles fine-tunés utilisant l'API OpenAI avec tool calls et sorties JSON.

## Problèmes Identifiés

### 1. Tool Calls Non Générés
**Symptôme:** Le modèle mentionne les outils dans sa réponse mais ne les appelle pas réellement.

**Causes possibles:**
- Le modèle fine-tuné n'a pas été entraîné sur des exemples de tool calls
- Le prompt n'est pas assez explicite
- Le modèle préfère répondre directement plutôt que d'appeler des outils

### 2. Formats JSON Invalides
**Symptôme:** Le modèle génère du JSON mal formé ou avec des erreurs de syntaxe.

**Causes possibles:**
- JSON tronqué ou incomplet
- Caractères d'échappement incorrects
- Structure imbriquée mal formée
- JSON mélangé avec du texte explicatif

### 3. Sémantique Incorrecte
**Symptôme:** Le JSON est syntaxiquement valide mais les données sont incohérentes.

**Exemples:**
- Valeur totale ne correspond pas à la somme des positions
- Calculs financiers avec résultats incohérents
- Champs requis manquants
- Types de données incorrects

## Solutions Implémentées

### 1. Détection et Validation des Tool Calls

#### `ToolCallDetector`
Classe utilitaire pour détecter et valider les appels d'outils.

```python
from app.mitigation_strategies import ToolCallDetector

# Extraire les tool calls
tool_calls = ToolCallDetector.extract_tool_calls(result)

# Valider que les outils requis ont été appelés
is_valid, errors = ToolCallDetector.validate_tool_calls_required(
    result,
    expected_tools=["calculer_valeur_future"],
    min_calls=1
)
```

#### Utilisation avec `SafeAgent`
```python
from app.mitigation_strategies import SafeAgent

safe_agent = SafeAgent(
    agent=base_agent,
    tool_call_required=True,
    expected_tools=["calculer_valeur_future"],
    max_retries=3
)

result, success, errors = await safe_agent.run_safe(prompt)
```

### 2. Validation des Formats JSON

#### `JSONValidator`
Classe pour valider la structure et extraire JSON du texte.

```python
from app.mitigation_strategies import JSONValidator

# Extraire JSON d'un texte (peut contenir du texte autour)
json_data = JSONValidator.extract_json_from_text(response_text)

# Valider la structure contre un modèle Pydantic
is_valid, error, validated = JSONValidator.validate_json_structure(
    json_data,
    PortfolioExtraction
)
```

#### Extraction Intelligente
Le validateur peut extraire JSON même s'il est entouré de texte:
- JSON dans des blocs de code (```json ... ```)
- JSON entre accolades dans un texte
- JSON partiellement formaté

### 3. Validation Sémantique

#### Validateurs Personnalisés
```python
from app.mitigation_strategies import create_portfolio_validator

validator = create_portfolio_validator()
is_valid, errors = validator(portfolio_data)
```

#### Validateur de Calculs Financiers
```python
from app.mitigation_strategies import create_calculation_validator

validator = create_calculation_validator()
is_valid, errors = validator(calculation_data)
```

### 4. Stratégies de Retry

#### Retry avec Validation
```python
from app.mitigation_strategies import RetryStrategy

result, success, errors = await RetryStrategy.retry_with_validation(
    agent=agent,
    prompt=prompt,
    output_type=PortfolioExtraction,
    max_retries=3,
    tool_call_required=True,
    expected_tools=["calculer_valeur_future"]
)
```

#### Retry avec Prompts de Fallback
Si le premier prompt échoue, essayer des prompts plus explicites:

```python
prompts = [
    "Calcule la valeur future de 25 000€ à 5% pendant 8 ans.",
    "QUESTION: Calcule la valeur future.\nPARAMÈTRES: capital=25000, taux=0.05, duree=8\nACTION: Appelle calculer_valeur_future",
    "Tu DOIS appeler calculer_valeur_future avec capital_initial=25000, taux_annuel=0.05, duree_annees=8"
]

result, success = await RetryStrategy.retry_with_fallback_prompt(
    agent=agent,
    prompts=prompts
)
```

### 5. Décorateurs de Validation

#### `@with_tool_call_validation`
```python
from app.mitigation_strategies import with_tool_call_validation

@with_tool_call_validation(
    expected_tools=["calculer_valeur_future"],
    min_calls=1,
    raise_on_failure=False
)
async def my_agent_function(question: str):
    return await agent.run(question)
```

#### `@with_json_validation`
```python
from app.mitigation_strategies import with_json_validation

@with_json_validation(
    output_type=PortfolioExtraction,
    extract_from_text=True,
    semantic_validator=create_portfolio_validator()
)
async def extract_portfolio(prompt: str):
    return await agent.run(prompt, output_type=PortfolioExtraction)
```

## Application aux Exemples Existants

### Agent 2 Tools (`agent_2_tools.py`)

**Problème:** Le modèle peut ne pas appeler les outils pour les calculs.

**Solution:**
```python
from app.mitigation_strategies import SafeAgent

# Wrapper l'agent existant
safe_finance_agent = SafeAgent(
    agent=finance_calculator_agent,
    tool_call_required=True,
    expected_tools=["calculer_valeur_future", "calculer_versement_mensuel"],
    max_retries=3
)

# Utiliser avec validation automatique
result, success, errors = await safe_finance_agent.run_safe(question)
```

### Agent 1 Structured Data (`agent_1_structured_data.py`)

**Problème:** JSON peut être mal formé ou incomplet.

**Solution:**
```python
from app.mitigation_strategies import SafeAgent, create_portfolio_validator

safe_extract_agent = SafeAgent(
    agent=extract_agent,
    output_type=Portfolio,
    max_retries=3,
    semantic_validator=create_portfolio_validator()
)

result, success, errors = await safe_extract_agent.run_safe(
    prompt,
    output_type=Portfolio
)
```

### Agent 2 Quant (`agent_2_tools_quant.py`)

**Problème:** Tool calls complexes avec plusieurs outils, risque d'échec.

**Solution:**
```python
from app.mitigation_strategies import SafeAgent

safe_quant_agent = SafeAgent(
    agent=quant_risk_agent,
    tool_call_required=True,
    expected_tools=["calculer_var_parametrique"],
    max_retries=3
)
```

### Agent 3 Multi-Step (`agent_3_multi_step.py`)

**Problème:** Workflow complexe avec plusieurs agents, validation nécessaire à chaque étape.

**Solution:**
```python
# Valider chaque étape du workflow
for step_name, agent, prompt in workflow_steps:
    safe_agent = SafeAgent(
        agent=agent,
        tool_call_required=True,
        max_retries=2
    )
    result, success, errors = await safe_agent.run_safe(prompt)
    
    if not success:
        # Gérer l'échec de l'étape
        handle_step_failure(step_name, errors)
```

## Bonnes Pratiques

### 1. Prompts Explicites pour Tool Calls
- ✅ "Appelle l'outil calculer_valeur_future avec capital_initial=25000, taux_annuel=0.05, duree_annees=8"
- ❌ "Calcule la valeur future de 25 000€ à 5% pendant 8 ans"

### 2. Validation en Plusieurs Étapes
1. Structure JSON (syntaxe)
2. Schéma Pydantic (types)
3. Sémantique (logique métier)

### 3. Retry avec Prompts Progressifs
- Tentative 1: Prompt naturel
- Tentative 2: Prompt plus explicite
- Tentative 3: Prompt très structuré avec instructions détaillées

### 4. Logging et Monitoring
```python
result, success, errors = await safe_agent.run_safe(prompt)

if not success:
    logger.warning(f"Agent failed: {errors}")
    # Envoyer des métriques
    metrics.increment("agent.failures", tags={"agent": agent_name})
```

### 5. Fallback Strategies
Si les retries échouent:
- Utiliser une valeur par défaut
- Demander clarification à l'utilisateur
- Escalader vers un agent plus puissant
- Retourner une erreur explicite

## Exemple Complet

Voir `examples/agent_with_mitigation.py` pour des exemples complets d'utilisation de toutes les stratégies.

## Tests

Les stratégies peuvent être testées avec:
```bash
python examples/agent_with_mitigation.py
```

## Performance

- **Retry:** Ajoute ~0.5-2s par tentative
- **Validation JSON:** Négligeable (<10ms)
- **Validation sémantique:** Dépend de la complexité (<50ms typiquement)

## Limitations

1. Les retries peuvent augmenter la latence
2. La validation sémantique nécessite des règles métier spécifiques
3. L'extraction JSON peut échouer sur des formats très irréguliers
4. Les tool calls peuvent ne pas être détectés si la structure change

## Améliorations Futures

- [ ] Détection automatique des patterns d'échec
- [ ] Apprentissage des prompts efficaces
- [ ] Validation sémantique basée sur ML
- [ ] Cache des validations pour améliorer les performances

