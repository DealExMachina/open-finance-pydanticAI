# Examples - PydanticAI avec Qwen-Open-Finance-R-8B

## 🎯 Exemples Recommandés (Modèle 8B)

### ✅ Commencer ici: Tests Simples
```bash
python3 examples/test_json_simple.py
```
**Résultat attendu**: 100% de succès (3/3 tests)

Ce test démontre que le modèle 8B **fonctionne parfaitement** avec:
- Schémas simples (Position, Portfolio)
- Prompts clairs avec exemples
- Volumes modestes (1-3 positions)

### ✅ Extraction de Portfolio
```bash
python3 examples/agent_1_structured_data.py
```
Extraction réelle de données financières depuis texte non structuré.

### 🔧 Tests avec Tool Calls
```bash
python3 examples/test_tool_calls_simple.py
```
Tests des capacités de tool calling du modèle.

### ⚠️ Tests Avancés (Attendez-vous à des échecs)
```bash
python3 examples/test_json_output_evaluation.py
```
Suite complète de 10 tests progressifs. Le modèle 8B échouera sur les tests complexes (c'est normal).

## 📚 Autres Exemples

### Exemples avec SafeAgent
- `agent_with_mitigation.py`: Agent avec validation et retry
- `agent_2_tools.py`: Agent avec outils de calcul
- `agent_2_tools_quant.py`: Agent quantitatif (nécessite QuantLib)

### Exemples Multi-Step
- `agent_3_multi_step.py`: Workflow complexe multi-agents
- `agent_option_pricing.py`: Pricing d'options (nécessite QuantLib)

## 🎓 Comment Interpréter les Résultats

### Tests Simples (test_json_simple.py)
- **100% succès**: ✅ Tout fonctionne correctement
- **<100% succès**: ⚠️ Problème de configuration ou connexion

### Tests Avancés (test_json_output_evaluation.py)
- **Tests 1-3**: Doivent passer (schémas simples)
- **Tests 4-7**: 50-70% attendu (schémas modérés)
- **Tests 8-10**: Échecs attendus (trop complexes pour 8B)

## 💡 Si les Tests Échouent

1. **Vérifier la connexion au modèle**:
```python
from app.models import finance_model
from pydantic_ai import Agent

agent = Agent(finance_model, system_prompt="Test")
result = await agent.run("Hello")
print(result.output)  # Doit afficher une réponse
```

2. **Vérifier l'accès aux résultats**:
Les résultats validés sont dans `result.output`, pas `result.data`:
```python
result = await agent.run(prompt, output_type=Portfolio)
portfolio = result.output  # ← C'est ici!
```

3. **Simplifier les schémas**:
Si un test échoue, c'est peut-être trop complexe pour un modèle 8B.

## 📖 Documentation Complète

Voir `docs/model_capabilities_8b.md` pour:
- Capacités et limitations détaillées
- Meilleures pratiques de prompting
- Patterns de code recommandés
- Guide de débogage

## 🚀 Quick Start

```bash
# Activer l'environnement
source venv/bin/activate

# Installer les dépendances
pip install -e .

# Lancer le test simple
python3 examples/test_json_simple.py

# Si succès (3/3), le modèle est prêt!
```

## 📊 Résultats Attendus (Modèle 8B)

| Test | Complexité | Succès Attendu | Notes |
|------|-----------|---------------|-------|
| test_json_simple.py | Faible | 100% (3/3) | Tests calibrés pour 8B |
| agent_1_structured_data.py | Faible | 100% | Extraction simple |
| test_tool_calls_simple.py | Moyenne | 75%+ | Tool calling |
| test_json_output_evaluation.py | Variable | 30-50% | Tests 1-3: OK, 8-10: KO |

**Conclusion**: Le modèle 8B est **performant et fiable** sur des tâches appropriées!
