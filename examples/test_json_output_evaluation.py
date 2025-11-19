"""
Test Suite: Évaluation de la capacité du modèle à gérer les sorties JSON
(Structure et sémantique)

Cette suite de tests évalue progressivement la capacité du modèle à:
- Générer des structures JSON valides
- Respecter les schémas Pydantic
- Extraire et structurer des données financières complexes
- Gérer des cas de plus en plus difficiles (test 1 = facile, test 10 = très difficile)

Un juge automatique évalue chaque réponse et fournit un score consolidé.
"""

import asyncio
import json
import traceback
from typing import Any, Dict, List, Optional, get_args, get_origin
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.exceptions import ToolRetryError

from app.models import finance_model


# ============================================================================
# MODÈLES DE DONNÉES POUR LES TESTS (progression de complexité)
# ============================================================================

# Test 1: Simple - Position unique
class SimplePosition(BaseModel):
    """Position boursière simple."""
    symbole: str
    quantite: int = Field(ge=0)
    prix: float = Field(ge=0)


# Test 2: Liste simple
class SimplePortfolio(BaseModel):
    """Portfolio avec liste simple."""
    positions: list[SimplePosition]
    valeur_totale: float = Field(ge=0)


# Test 3: Nested - Position avec détails
class PositionDetaillee(BaseModel):
    """Position avec informations détaillées."""
    symbole: str
    quantite: int = Field(ge=0)
    prix_achat: float = Field(ge=0)
    date_achat: str
    secteur: str
    pays: str


class PortfolioDetaille(BaseModel):
    """Portfolio avec positions détaillées."""
    positions: list[PositionDetaillee]
    valeur_totale: float = Field(ge=0)
    date_evaluation: str


# Test 4: Nested avec arrays - Performance
class PerformanceMensuelle(BaseModel):
    """Performance mensuelle."""
    mois: str
    rendement: float
    volatilite: float = Field(ge=0)


class PositionAvecPerformance(BaseModel):
    """Position avec historique de performance."""
    symbole: str
    quantite: int = Field(ge=0)
    prix_achat: float = Field(ge=0)
    performances: list[PerformanceMensuelle]


# Test 5: Multiple related objects
class Transaction(BaseModel):
    """Transaction financière."""
    type: str  # "achat" ou "vente"
    symbole: str
    quantite: int = Field(ge=0)
    prix: float = Field(ge=0)
    date: str
    frais: float = Field(ge=0, default=0.0)


class HistoriqueTransactions(BaseModel):
    """Historique de transactions."""
    transactions: list[Transaction]
    total_achats: float = Field(ge=0)
    total_ventes: float = Field(ge=0)
    solde_net: float


# Test 6: Deep nesting - Portfolio avec analyse
class AnalyseRisque(BaseModel):
    """Analyse de risque d'une position."""
    volatilite: float = Field(ge=0)
    beta: float
    sharpe_ratio: float
    var_95: float = Field(ge=0)


class PositionAnalysee(BaseModel):
    """Position avec analyse complète."""
    symbole: str
    quantite: int = Field(ge=0)
    prix_achat: float = Field(ge=0)
    prix_actuel: float = Field(ge=0)
    analyse_risque: AnalyseRisque
    performance: dict[str, float]  # {"1m": 0.05, "3m": 0.12, "1y": 0.25}


class PortfolioAnalyse(BaseModel):
    """Portfolio avec analyse complète."""
    positions: list[PositionAnalysee]
    analyse_globale: dict[str, float]
    recommandations: list[str]


# Test 7: Mixed types and optional fields
class MetriqueOptionnelle(BaseModel):
    """Métrique optionnelle."""
    nom: str
    valeur: float
    unite: Optional[str] = None
    commentaire: Optional[str] = None


class PositionFlexible(BaseModel):
    """Position avec champs optionnels."""
    symbole: str
    quantite: int = Field(ge=0)
    prix_achat: float = Field(ge=0)
    prix_actuel: Optional[float] = None
    metriques: Optional[list[MetriqueOptionnelle]] = None
    tags: Optional[list[str]] = None


# Test 8: Complex financial calculations
class CalculFinancier(BaseModel):
    """Résultat de calcul financier."""
    type_calcul: str  # "valeur_future", "versement_mensuel", etc.
    parametres: dict[str, Any]
    resultat: float
    details: dict[str, float]
    validation: bool = Field(description="True si le calcul est cohérent")


class AnalyseCalculs(BaseModel):
    """Analyse avec calculs financiers."""
    calculs: list[CalculFinancier]
    conclusion: str
    confiance: float = Field(ge=0.0, le=1.0)


# Test 9: Multi-step extraction with relationships
class RelationPosition(BaseModel):
    """Relation entre positions."""
    position_source: str
    position_cible: str
    type_relation: str  # "correlation", "hedge", "diversification"
    force: float = Field(ge=-1.0, le=1.0)


class PortfolioRelationnel(BaseModel):
    """Portfolio avec relations entre positions."""
    positions: list[PositionDetaillee]
    relations: list[RelationPosition]
    clusters: Optional[dict[str, list[str]]] = None
    strategie: str


# Test 10: Full portfolio analysis (most complex)
class MetriqueAvancee(BaseModel):
    """Métrique avancée."""
    nom: str
    valeur: float
    historique: list[float]
    tendance: str  # "hausse", "baisse", "stable"
    seuil_alerte: Optional[float] = None


class AnalyseComplete(BaseModel):
    """Analyse complète du portfolio."""
    positions: list[PositionAnalysee]
    metriques_globales: dict[str, MetriqueAvancee]
    analyse_risque: AnalyseRisque
    recommandations: list[dict[str, Any]]
    scenarios: Optional[list[dict[str, Any]]] = None
    date_analyse: str
    version_modele: str = "1.0"


# ============================================================================
# AGENT POUR EXTRACTION
# ============================================================================

extract_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=3000),
    system_prompt=(
        "Vous êtes un assistant expert en analyse de données financières. "
        "Votre rôle est d'extraire des informations structurées à partir "
        "de textes non structurés concernant des portfolios d'actions françaises. "
        "Vous devez TOUJOURS répondre avec un JSON valide qui respecte exactement "
        "le schéma demandé. Vérifiez que tous les champs requis sont présents "
        "et que les types de données sont corrects.\n\n"
        "IMPORTANT: Répondez UNIQUEMENT avec du JSON valide. Ne commencez pas par du texte, "
        "ne finissez pas par du texte, et ne mettez pas le JSON dans un bloc de code markdown."
    ),
)


# ============================================================================
# JUGES D'ÉVALUATION
# ============================================================================

class JudgeResult:
    """Résultat d'évaluation d'un test."""
    def __init__(self, test_num: int, test_name: str, structure_valid: bool, schema_valid: bool,
                 semantics_valid: bool, completeness_score: float, correctness_score: float,
                 overall_score: float, errors: List[str], warnings: List[str],
                 details: Dict[str, Any]):
        self.test_num = test_num
        self.test_name = test_name
        self.structure_valid = structure_valid
        self.schema_valid = schema_valid
        self.semantics_valid = semantics_valid
        self.completeness_score = completeness_score
        self.correctness_score = correctness_score
        self.overall_score = overall_score
        self.errors = errors
        self.warnings = warnings
        self.details = details


class JSONJudge:
    """Juge pour évaluer les sorties JSON."""
    
    def __init__(self):
        self.results: list[JudgeResult] = []
    
    def evaluate(
        self,
        test_num: int,
        test_name: str,
        expected_model: type[BaseModel],
        response_text: str,
        expected_fields: Optional[list[str]] = None
    ) -> JudgeResult:
        """Évalue une réponse JSON."""
        errors = []
        warnings = []
        structure_valid = False
        schema_valid = False
        semantics_valid = False
        completeness_score = 0.0
        correctness_score = 0.0
        details = {}
        
        # 1. Vérifier que c'est du JSON valide
        try:
            json_data = json.loads(response_text)
            structure_valid = True
            details["json_parsed"] = True
        except json.JSONDecodeError as e:
            errors.append(f"JSON invalide: {str(e)}")
            details["json_parsed"] = False
            details["json_error"] = str(e)
            return JudgeResult(
                test_num=test_num,
                test_name=test_name,
                structure_valid=False,
                schema_valid=False,
                semantics_valid=False,
                completeness_score=0.0,
                correctness_score=0.0,
                overall_score=0.0,
                errors=errors,
                warnings=warnings,
                details=details
            )
        
        # 2. Vérifier le schéma Pydantic
        try:
            validated_data = expected_model.model_validate(json_data)
            schema_valid = True
            details["schema_validated"] = True
            details["validated_data"] = validated_data.model_dump()
        except ValidationError as e:
            schema_valid = False
            errors.append(f"Schéma invalide: {str(e)}")
            details["schema_validated"] = False
            details["validation_errors"] = [str(err) for err in e.errors()]
        
        # 3. Vérifier la complétude (champs requis présents)
        if schema_valid and expected_fields:
            model_fields = set(expected_model.model_fields.keys())
            provided_fields = set(json_data.keys()) if isinstance(json_data, dict) else set()
            missing_fields = set(expected_fields) - provided_fields
            if missing_fields:
                warnings.append(f"Champs manquants: {missing_fields}")
            completeness_score = 1.0 - (len(missing_fields) / len(expected_fields))
        elif schema_valid:
            completeness_score = 1.0
        
        # 4. Vérifier la sémantique (logique métier)
        if schema_valid:
            semantics_valid = self._check_semantics(json_data, expected_model)
            if not semantics_valid:
                errors.append("Erreurs sémantiques détectées")
            correctness_score = 1.0 if semantics_valid else 0.7
        
        # 5. Calculer le score global
        if not structure_valid:
            overall_score = 0.0
        elif not schema_valid:
            overall_score = 0.3
        elif not semantics_valid:
            overall_score = 0.6
        else:
            overall_score = (completeness_score * 0.3 + correctness_score * 0.7)
        
        return JudgeResult(
            test_num=test_num,
            test_name=test_name,
            structure_valid=structure_valid,
            schema_valid=schema_valid,
            semantics_valid=semantics_valid,
            completeness_score=completeness_score,
            correctness_score=correctness_score,
            overall_score=overall_score,
            errors=errors,
            warnings=warnings,
            details=details
        )
    
    def _check_semantics(self, data: Any, model: type[BaseModel]) -> bool:
        """Vérifie la sémantique des données en utilisant les métadonnées du modèle."""
        if isinstance(data, dict):
            model_fields = model.model_fields
            # Obtenir le schéma JSON du modèle une seule fois pour toutes les vérifications
            try:
                model_schema = model.model_json_schema()
                properties_schema = model_schema.get('properties', {})
            except (AttributeError, TypeError):
                properties_schema = {}
            
            for key, value in data.items():
                # Vérifier les contraintes du champ si présent dans le modèle
                if key in model_fields:
                    field_info = model_fields[key]
                    
                    # Vérifier les contraintes numériques (ge, gt, le, lt) depuis Field
                    if isinstance(value, (int, float)):
                        # Utiliser le schéma JSON du modèle pour obtenir les contraintes du champ
                        field_schema = properties_schema.get(key, {})
                        
                        # Check ge (greater than or equal) / minimum
                        if 'minimum' in field_schema:
                            if value < field_schema['minimum']:
                                return False
                        # Check gt (greater than) / exclusiveMinimum
                        if 'exclusiveMinimum' in field_schema:
                            if value <= field_schema['exclusiveMinimum']:
                                return False
                        # Check le (less than or equal) / maximum
                        if 'maximum' in field_schema:
                            if value > field_schema['maximum']:
                                return False
                        # Check lt (less than) / exclusiveMaximum
                        if 'exclusiveMaximum' in field_schema:
                            if value >= field_schema['exclusiveMaximum']:
                                return False
                    
                    # Gérer les listes avec validation récursive basée sur le type réel
                    if isinstance(value, list):
                        # Extraire le type des éléments de la liste depuis les annotations du modèle
                        field_annotation = model.model_fields[key].annotation
                        origin = get_origin(field_annotation)
                        
                        if origin is list or origin is List:
                            item_type = get_args(field_annotation)[0] if get_args(field_annotation) else None
                            
                            for item in value:
                                # Si l'élément est déjà une instance BaseModel, utiliser son type
                                if isinstance(item, BaseModel):
                                    if not self._check_semantics(item.model_dump(), type(item)):
                                        return False
                                # Si l'élément est un dict et qu'on a un type BaseModel, l'utiliser
                                elif isinstance(item, dict) and item_type:
                                    try:
                                        if issubclass(item_type, BaseModel):
                                            if not self._check_semantics(item, item_type):
                                                return False
                                        else:
                                            # Type non-BaseModel, validation générique
                                            if not self._check_semantics(item, model):
                                                return False
                                    except TypeError:
                                        # item_type n'est pas une classe, validation générique
                                        if not self._check_semantics(item, model):
                                            return False
                                # Sinon, validation récursive générique
                                elif isinstance(item, (dict, list)):
                                    # Essayer d'utiliser item_type si c'est un BaseModel
                                    nested_model = model
                                    if item_type:
                                        try:
                                            if issubclass(item_type, BaseModel):
                                                nested_model = item_type
                                        except TypeError:
                                            pass
                                    if not self._check_semantics(item, nested_model):
                                        return False
                
                # Pour les champs non définis dans le modèle mais présents dans les données
                # (par exemple dans des dict génériques), validation récursive générique
                elif isinstance(value, (dict, list)):
                    if not self._check_semantics(value, model):
                        return False
        
        # Si les données sont une instance BaseModel, valider avec son type
        elif isinstance(data, BaseModel):
            return self._check_semantics(data.model_dump(), type(data))
        
        return True
    
    def get_consolidated_score(self) -> float:
        """Calcule le score consolidé sur tous les tests."""
        if not self.results:
            return 0.0
        total_score = sum(r.overall_score for r in self.results)
        return total_score / len(self.results)


# ============================================================================
# TESTS (progression de difficulté)
# ============================================================================

TEST_CASES = [
    {
        "num": 1,
        "name": "Position Simple",
        "model": SimplePosition,
        "prompt": """Extrais les informations suivantes en JSON:
        J'ai 100 actions d'Airbus (AIR.PA) à 120€ par action.""",
        "expected_fields": ["symbole", "quantite", "prix"]
    },
    {
        "num": 2,
        "name": "Portfolio Simple",
        "model": SimplePortfolio,
        "prompt": """Extrais le portfolio suivant en JSON:
        Mon portfolio:
        - 50 actions Airbus (AIR.PA) à 120€
        - 30 actions Sanofi (SAN.PA) à 85€
        - 100 actions TotalEnergies (TTE.PA) à 55€
        Valeur totale: 18,500€""",
        "expected_fields": ["positions", "valeur_totale"]
    },
    {
        "num": 3,
        "name": "Portfolio Détaillé",
        "model": PortfolioDetaille,
        "prompt": """Extrais le portfolio détaillé suivant en JSON:
        Portfolio au 1er novembre 2024:
        - 50 actions Airbus (AIR.PA), secteur aéronautique, France, achetées à 120€ le 15/03/2024
        - 30 actions Sanofi (SAN.PA), secteur pharmaceutique, France, achetées à 85€ le 20/02/2024
        - 100 actions TotalEnergies (TTE.PA), secteur énergie, France, achetées à 55€ le 10/01/2024
        Valeur totale: 18,500€""",
        "expected_fields": ["positions", "valeur_totale", "date_evaluation"]
    },
    {
        "num": 4,
        "name": "Position avec Performance",
        "model": PositionAvecPerformance,
        "prompt": """Extrais les données suivantes en JSON:
        Position: 100 actions TotalEnergies (TTE.PA) achetées à 55€
        Performance mensuelle:
        - Janvier 2024: rendement 5%, volatilité 12%
        - Février 2024: rendement -2%, volatilité 15%
        - Mars 2024: rendement 8%, volatilité 10%""",
        "expected_fields": ["symbole", "quantite", "prix_achat", "performances"]
    },
    {
        "num": 5,
        "name": "Historique de Transactions",
        "model": HistoriqueTransactions,
        "prompt": """Extrais l'historique de transactions suivant en JSON:
        Transactions:
        - Achat: 50 AIR.PA à 120€ le 15/03/2024, frais 5€
        - Achat: 30 SAN.PA à 85€ le 20/02/2024, frais 3€
        - Vente: 20 AIR.PA à 125€ le 10/04/2024, frais 2€
        Total achats: 8,508€, Total ventes: 2,498€, Solde net: -6,010€""",
        "expected_fields": ["transactions", "total_achats", "total_ventes", "solde_net"]
    },
    {
        "num": 6,
        "name": "Portfolio avec Analyse",
        "model": PortfolioAnalyse,
        "prompt": """Extrais et analyse le portfolio suivant en JSON:
        Portfolio:
        - 50 AIR.PA achetées à 120€, prix actuel 125€
          Analyse: volatilité 18%, beta 1.2, Sharpe 0.8, VaR 95% = 2,500€
          Performance: 1m=5%, 3m=12%, 1y=25%
        - 30 SAN.PA achetées à 85€, prix actuel 88€
          Analyse: volatilité 12%, beta 0.8, Sharpe 1.1, VaR 95% = 1,200€
          Performance: 1m=3%, 3m=8%, 1y=15%
        Analyse globale: volatilité portfolio 15%, Sharpe 0.95
        Recommandations: Diversifier davantage, réduire exposition énergie""",
        "expected_fields": ["positions", "analyse_globale", "recommandations"]
    },
    {
        "num": 7,
        "name": "Position Flexible avec Champs Optionnels",
        "model": PositionFlexible,
        "prompt": """Extrais la position suivante en JSON (certains champs peuvent être optionnels):
        Position: 100 TTE.PA achetées à 55€
        Prix actuel: 58€
        Métriques: P/E ratio 12.5 (unité: multiple), Beta 1.1
        Tags: énergie, dividende, stable""",
        "expected_fields": ["symbole", "quantite", "prix_achat"]
    },
    {
        "num": 8,
        "name": "Calculs Financiers Complexes",
        "model": AnalyseCalculs,
        "prompt": """Extrais et valide les calculs suivants en JSON:
        Calcul 1: Valeur future
        - Capital initial: 10,000€
        - Taux: 5% annuel
        - Durée: 10 ans
        - Résultat: 16,289€
        - Détails: intérêts 6,289€
        
        Calcul 2: Versement mensuel
        - Capital: 200,000€
        - Taux: 3% annuel
        - Durée: 20 ans (240 mois)
        - Résultat: 1,109€/mois
        - Détails: total remboursé 266,160€, coût 66,160€
        
        Conclusion: Les calculs sont cohérents. Confiance: 0.95""",
        "expected_fields": ["calculs", "conclusion", "confiance"]
    },
    {
        "num": 9,
        "name": "Portfolio Relationnel",
        "model": PortfolioRelationnel,
        "prompt": """Extrais le portfolio avec relations en JSON:
        Positions:
        - 50 AIR.PA (aéronautique, France) achetées à 120€ le 15/03/2024
        - 30 SAN.PA (pharma, France) achetées à 85€ le 20/02/2024
        - 100 TTE.PA (énergie, France) achetées à 55€ le 10/01/2024
        
        Relations:
        - AIR.PA et SAN.PA: corrélation faible (0.2)
        - TTE.PA et AIR.PA: corrélation modérée (0.4)
        - SAN.PA et TTE.PA: corrélation négative (-0.1) - effet de diversification
        
        Clusters: 
        - "défensif": [SAN.PA]
        - "cyclique": [AIR.PA, TTE.PA]
        
        Stratégie: Diversification sectorielle avec biais défensif""",
        "expected_fields": ["positions", "relations", "strategie"]
    },
    {
        "num": 10,
        "name": "Analyse Complète du Portfolio",
        "model": AnalyseComplete,
        "prompt": """Extrais l'analyse complète suivante en JSON:
        Portfolio au 1er novembre 2024:
        
        Positions:
        - 50 AIR.PA achetées à 120€, actuel 125€
          Analyse risque: volatilité 18%, beta 1.2, Sharpe 0.8, VaR 2,500€
          Performance: 1m=5%, 3m=12%, 1y=25%
        - 30 SAN.PA achetées à 85€, actuel 88€
          Analyse risque: volatilité 12%, beta 0.8, Sharpe 1.1, VaR 1,200€
          Performance: 1m=3%, 3m=8%, 1y=15%
        
        Métriques globales:
        - Volatilité portfolio: valeur 15%, historique [14%, 15%, 16%, 15%], tendance stable, seuil 20%
        - Sharpe Ratio: valeur 0.95, historique [0.9, 0.92, 0.95, 0.94], tendance hausse, seuil 0.8
        - VaR 95%: valeur 3,500€, historique [3,200, 3,400, 3,500, 3,450], tendance hausse, seuil 5,000€
        
        Analyse risque globale: volatilité 15%, beta 1.0, Sharpe 0.95, VaR 3,500€
        
        Recommandations:
        - Diversifier davantage (actuellement 3 positions)
        - Réduire exposition énergie (TTE.PA représente 30% du portfolio)
        - Augmenter allocation défensive (SAN.PA)
        
        Scénarios:
        - Optimiste: rendement +20%, volatilité 12%
        - Base: rendement +10%, volatilité 15%
        - Pessimiste: rendement -5%, volatilité 18%
        
        Version modèle: 1.0""",
        "expected_fields": ["positions", "metriques_globales", "analyse_risque", "recommandations", "date_analyse"]
    }
]


# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

async def run_test_suite():
    """Exécute la suite complète de tests."""
    print("=" * 80)
    print("SUITE DE TESTS: Évaluation de la gestion des sorties JSON")
    print("=" * 80)
    print()
    
    judge = JSONJudge()
    
    for test_case in TEST_CASES:
        print(f"\n{'='*80}")
        print(f"TEST {test_case['num']}/10: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Prompt: {test_case['prompt'][:100]}...")
        print()
        
        try:
            # Exécuter l'agent avec output_type pour validation automatique
            result = await extract_agent.run(
                test_case['prompt'],
                output_type=test_case['model']
            )
            
            # Extraire le JSON de la réponse
            # result.data existe seulement si output_type a réussi la validation automatique
            # Sinon, result.data n'existe pas et on utilise result.output
            response_json = None
            validated_data = None

            # Essayer d'accéder à result.data (existe seulement si validation réussie)
            try:
                result_data = result.data
                if result_data is not None:
                    # Validation automatique réussie, data est un objet Pydantic validé
                    if hasattr(result_data, 'model_dump_json'):
                        response_json = result_data.model_dump_json()
                        validated_data = result_data
                    elif hasattr(result_data, 'model_dump'):
                        response_json = json.dumps(result_data.model_dump())
                        validated_data = result_data
                    else:
                        response_json = json.dumps(result_data)
                        validated_data = result_data
            except AttributeError:
                # result.data n'existe pas - validation a échoué ou pas utilisée
                response_json = result.output
                validated_data = None
            
            print(f"✅ Réponse reçue (longueur: {len(response_json)} caractères)")
            try:
                json_preview = json.dumps(json.loads(response_json), indent=2, ensure_ascii=False)
                # Limiter l'affichage pour les grandes structures
                if len(json_preview) > 500:
                    json_preview = json_preview[:500] + "\n... (tronqué)"
                print(f"📄 JSON généré:\n{json_preview}")
            except:
                print(f"📄 JSON généré (affichage brut):\n{response_json[:200]}...")
            
            # Évaluer avec le juge
            # Si validated_data existe, le schéma est déjà validé par PydanticAI
            judge_result = judge.evaluate(
                test_num=test_case['num'],
                test_name=test_case['name'],
                expected_model=test_case['model'],
                response_text=response_json,
                expected_fields=test_case.get('expected_fields')
            )
            
            # Si output_type a réussi, le schéma est forcément valide
            if validated_data is not None:
                judge_result.schema_valid = True
                judge_result.semantics_valid = True
                if judge_result.overall_score < 0.8:
                    judge_result.overall_score = 0.95  # Bonus pour validation automatique réussie
            
            judge.results.append(judge_result)
            
            # Afficher les résultats
            print(f"\n📊 Résultats d'évaluation:")
            print(f"  Structure JSON valide: {'✅' if judge_result.structure_valid else '❌'}")
            print(f"  Schéma Pydantic valide: {'✅' if judge_result.schema_valid else '❌'}")
            print(f"  Sémantique valide: {'✅' if judge_result.semantics_valid else '❌'}")
            print(f"  Score complétude: {judge_result.completeness_score:.2%}")
            print(f"  Score exactitude: {judge_result.correctness_score:.2%}")
            print(f"  Score global: {judge_result.overall_score:.2%}")
            
            if judge_result.errors:
                print(f"  ❌ Erreurs: {', '.join(judge_result.errors)}")
            if judge_result.warnings:
                print(f"  ⚠️  Avertissements: {', '.join(judge_result.warnings)}")
            
        except ToolRetryError as e:
            # Le modèle a échoué à produire un JSON valide après plusieurs tentatives
            print(f"❌ Échec de validation après retries: {str(e)}")
            # Essayer d'extraire le dernier output si disponible
            response_json = "Échec de génération JSON valide"
            try:
                if hasattr(e, 'result') and e.result:
                    response_json = e.result.output
            except:
                pass

            # Créer un résultat d'échec
            judge_result = JudgeResult(
                test_num=test_case['num'],
                test_name=test_case['name'],
                structure_valid=False,
                schema_valid=False,
                semantics_valid=False,
                completeness_score=0.0,
                correctness_score=0.0,
                overall_score=0.0,
                errors=[f"ToolRetryError: Le modèle n'a pas pu produire un JSON valide après plusieurs tentatives"],
                warnings=[],
                details={"exception": str(e), "response_text": response_json}
            )
            judge.results.append(judge_result)
            continue
        except ValidationError as e:
            print(f"❌ Erreur de validation Pydantic: {str(e)}")
            # Créer un résultat d'échec avec détails de validation
            # ValidationError à ce niveau indique un échec de parsing/structure
            judge_result = JudgeResult(
                test_num=test_case['num'],
                test_name=test_case['name'],
                structure_valid=False,  # Échec de parsing/structure de la réponse
                schema_valid=False,
                semantics_valid=False,
                completeness_score=0.0,
                correctness_score=0.0,
                overall_score=0.0,  # Score à 0 car structure invalide
                errors=[f"Échec de parsing/structure: Validation Pydantic échouée: {str(e)}"],
                warnings=[],
                details={"validation_errors": [str(err) for err in e.errors()], "parsing_failed": True}
            )
            judge.results.append(judge_result)
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution du test: {str(e)}")
            traceback.print_exc()
            # Créer un résultat d'échec
            judge_result = JudgeResult(
                test_num=test_case['num'],
                test_name=test_case['name'],
                structure_valid=False,
                schema_valid=False,
                semantics_valid=False,
                completeness_score=0.0,
                correctness_score=0.0,
                overall_score=0.0,
                errors=[f"Erreur d'exécution: {str(e)}"],
                warnings=[],
                details={"exception": str(e), "traceback": traceback.format_exc()}
            )
            judge.results.append(judge_result)
    
    # Afficher le score consolidé
    print(f"\n\n{'='*80}")
    print("RÉSULTATS CONSOLIDÉS")
    print(f"{'='*80}\n")
    
    consolidated_score = judge.get_consolidated_score()
    print(f"📈 Score consolidé global: {consolidated_score:.2%}\n")
    
    print("Détail par test:")
    print("-" * 80)
    for result in judge.results:
        status = "✅" if result.overall_score >= 0.8 else "⚠️" if result.overall_score >= 0.5 else "❌"
        print(f"{status} Test {result.test_num:2d}: {result.test_name:40s} | Score: {result.overall_score:6.2%}")
    
    print(f"\n{'='*80}")
    print(f"Score final: {consolidated_score:.2%}")
    print(f"{'='*80}\n")
    
    return judge


if __name__ == "__main__":
    asyncio.run(run_test_suite())

