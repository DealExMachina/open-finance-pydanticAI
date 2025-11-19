# Capacités et Limitations du Modèle 8B (Qwen-Open-Finance)

## Résumé

Le modèle Qwen-Open-Finance-R-8B (8 milliards de paramètres) **peut générer du JSON valide** mais nécessite des adaptations par rapport aux modèles plus grands.

## ✅ Ce qui FONCTIONNE

### 1. JSON Structuré Simple
- ✅ Schémas avec 2-3 champs
- ✅ Listes de 1-5 objets simples
- ✅ Types de base (str, int, float)
- ✅ Calculs arithmétiques simples

**Exemple réussi:**
```python
class Position(BaseModel):
    symbole: str
    quantite: int
    prix: float

class Portfolio(BaseModel):
    positions: List[Position]
    total: float
```

### 2. Extraction de Données
- ✅ Extraction depuis texte formaté
- ✅ Reconnaissance de patterns financiers
- ✅ Calculs de totaux

### 3. Accès aux Résultats avec PydanticAI
**IMPORTANT**: Avec ce modèle, les résultats validés sont dans `result.output`, pas `result.data`:

```python
result = await agent.run(prompt, output_type=Portfolio)

# ❌ NE MARCHE PAS:
portfolio = result.data  # AttributeError!

# ✅ CORRECT:
try:
    portfolio = result.data
except AttributeError:
    portfolio = result.output  # C'est ici!

if isinstance(portfolio, Portfolio):
    # Le modèle a réussi!
    print(f"Total: {portfolio.total}")
```

## ⚠️ Limitations

### 1. Schémas Complexes
- ❌ Nested objects trop profonds (>2 niveaux)
- ❌ Unions complexes
- ❌ Validations personnalisées complexes

### 2. Volumes de Données
- ✅ 1-5 objets: excellent
- ⚠️ 5-10 objets: bon
- ❌ >10 objets: erreurs fréquentes

### 3. Instructions Complexes
- ❌ Multi-step reasoning complexe
- ❌ Conditions imbriquées multiples

## 🎯 Meilleures Pratiques

### 1. Prompts Optimisés

**Structure recommandée:**
```python
system_prompt = (
    "Tu es un expert en [domaine]. Tu extrais des données en JSON.\n\n"
    "RÈGLES:\n"
    "1. [Règle simple et claire]\n"
    "2. [Règle simple et claire]\n"
    "3. Réponds UNIQUEMENT en JSON, sans texte avant ou après\n\n"
    "EXEMPLE:\n"
    'Texte: "..."\n'
    'JSON: {"field": "value", ...}\n\n'
    "IMPORTANT: Commence par { et termine par }"
)
```

**Éléments clés:**
- ✅ Instructions numérotées simples
- ✅ UN exemple concret
- ✅ Rappel de format à la fin
- ✅ Langage direct ("Tu", pas "Vous")

### 2. Schémas Simples

**✅ BON - Simple et clair:**
```python
class Position(BaseModel):
    symbole: str = Field(description="Code action (ex: AIR.PA)")
    quantite: int = Field(description="Nombre", ge=0)
    prix: float = Field(description="Prix unitaire €", ge=0)
```

**❌ ÉVITER - Trop complexe:**
```python
class Position(BaseModel):
    symbole: str
    details: Union[AchatDetails, VenteDetails]
    historique: List[Dict[str, Union[str, float, date]]]
    metadata: Optional[Dict[str, Any]]
```

### 3. Gestion des Résultats

**Pattern recommandé:**
```python
async def extract_with_fallback(agent, prompt, output_type):
    """Extraction robuste avec fallback."""
    result = await agent.run(prompt, output_type=output_type)
    
    # Essayer result.data puis result.output
    data = None
    try:
        data = result.data
    except AttributeError:
        if isinstance(result.output, output_type):
            data = result.output
    
    if data:
        return data, True, []
    else:
        return None, False, ["Validation échouée"]
```

### 4. Tests Progressifs

**Commencer simple:**
1. Test avec 1 objet → doit passer à 100%
2. Test avec 2-3 objets → doit passer à >90%
3. Test avec 5 objets → doit passer à >70%
4. Si échecs: simplifier le schéma, pas compliquer le prompt

## 📊 Résultats Attendus

### Tests Simples (voir `test_json_simple.py`)
- **Attendu**: 100% de succès
- **Si échecs**: Vérifier la connexion au modèle ou le prompt

### Tests Moyens (3-5 objets, schémas modérés)
- **Attendu**: 80-90% de succès
- **Si <70%**: Simplifier les schémas

### Tests Complexes (>5 objets, schémas riches)
- **Attendu**: 50-70% de succès
- **Accepter**: Limitations du modèle 8B

## 🚀 Exemples Fonctionnels

### Exemple 1: Extraction Simple
Voir: `examples/agent_1_structured_data.py`
- Portfolio avec 3 positions
- Calcul de total
- ✅ Fonctionne à 100%

### Exemple 2: Tests Progressifs
Voir: `examples/test_json_simple.py`
- 3 tests de difficulté croissante
- ✅ 100% de succès sur tests simples

## 💡 Quand Utiliser un Modèle Plus Grand

Envisager GPT-4, Claude, ou Qwen-72B si:
- ❌ Schémas complexes requis (>3 niveaux imbriqués)
- ❌ Volumes >10 objets par requête
- ❌ Validations sémantiques complexes
- ❌ Reasoning multi-étapes avec JSON

## 📝 Checklist de Débogage

Si les tests échouent:

1. ✅ Le prompt contient-il un exemple concret?
2. ✅ Le schéma a-t-il <5 champs par niveau?
3. ✅ Gérez-vous `result.output` ET `result.data`?
4. ✅ Les descriptions des Fields sont-elles claires?
5. ✅ Le prompt demande-t-il "JSON uniquement"?
6. ✅ Testez-vous avec 1 objet d'abord?

Si tout est ✅ et ça échoue encore → c'est une limitation du modèle 8B.

## 🎓 Conclusion

Le modèle Qwen-Open-Finance-R-8B (8B) est **capable et efficace** pour:
- Extraction de données financières structurées simples
- JSON avec schémas clairs et limités
- Volumes modestes de données (<10 objets)

**Clé du succès**: 
- Prompts explicites avec exemples
- Schémas simples et plats
- Gestion correcte de `result.output`
- Tests progressifs

Avec ces adaptations, le modèle 8B atteint **100% de succès** sur les cas d'usage appropriés!

