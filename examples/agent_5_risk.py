"""
Agent 5 Risk: Risk Assessment Agent for SWIFT/ISO 20022 Messages

This agent scores financial messages in a risk matrix and highlights suspect messages.
Risk factors include:
- Transaction amount thresholds
- High-risk countries/jurisdictions
- Unusual patterns (round numbers, rapid succession)
- Missing or inconsistent data
- Sanctions list matching
- PEP (Politically Exposed Person) screening
- Geographic risk
- Time-based anomalies
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings, Tool

from app.models import finance_model


# ============================================================================
# RISK MODELS
# ============================================================================

class RiskScore(BaseModel):
    """Risk score for a financial message."""
    overall_risk_score: float = Field(description="Overall risk score (0.0-1.0)", ge=0.0, le=1.0)
    risk_level: str = Field(description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    risk_factors: List[str] = Field(description="List of identified risk factors")
    risk_matrix: Dict[str, float] = Field(description="Risk scores by category")
    is_suspect: bool = Field(description="Whether message is flagged as suspect")
    recommendations: List[str] = Field(description="Recommendations for risk mitigation")


# ============================================================================
# RISK ASSESSMENT TOOLS
# ============================================================================

# High-risk countries/jurisdictions (simplified list - in production, use comprehensive sanctions lists)
HIGH_RISK_COUNTRIES = {
    "AF", "KP", "IR", "SY", "SD", "BY", "MM", "VE", "CU", "RU"
}

# High-risk country names (for name matching)
HIGH_RISK_COUNTRY_NAMES = {
    "afghanistan", "north korea", "iran", "syria", "sudan", 
    "belarus", "myanmar", "venezuela", "cuba", "russia"
}

# PEP keywords (simplified - in production, use comprehensive PEP databases)
PEP_KEYWORDS = {
    "minister", "president", "ambassador", "governor", "senator",
    "mayor", "judge", "general", "colonel", "director"
}

# Sanctioned entities (simplified - in production, use OFAC, UN, EU sanctions lists)
SANCTIONED_ENTITIES = {
    "terrorist", "drug cartel", "organized crime", "money laundering"
}


def calculer_score_risque_montant(amount: float, currency: str = "EUR") -> Dict[str, Any]:
    """Calculate risk score based on transaction amount.
    
    Risk increases with:
    - Very large amounts (>100k EUR)
    - Round numbers (potential structuring)
    - Unusual amounts (e.g., 99,999 to avoid reporting)
    
    Args:
        amount: Transaction amount
        currency: Currency code
        
    Returns:
        Dict with risk_score (0.0-1.0), risk_factors, and details
    """
    risk_score = 0.0
    risk_factors = []
    details = {}
    
    # Convert to EUR for comparison (simplified - in production, use real exchange rates)
    eur_amount = amount
    if currency != "EUR":
        # Rough conversion (in production, use real rates)
        conversion_rates = {"USD": 0.92, "GBP": 1.17, "CHF": 1.05}
        eur_amount = amount * conversion_rates.get(currency, 1.0)
    
    # Risk factor 1: Very large amounts
    if eur_amount > 100000:
        risk_score += 0.3
        risk_factors.append(f"Very large amount: {amount:,.2f} {currency} (>100k EUR)")
        details["amount_threshold"] = "HIGH"
    elif eur_amount > 50000:
        risk_score += 0.15
        risk_factors.append(f"Large amount: {amount:,.2f} {currency} (>50k EUR)")
        details["amount_threshold"] = "MEDIUM"
    elif eur_amount > 10000:
        risk_score += 0.05
        details["amount_threshold"] = "LOW"
    
    # Risk factor 2: Round numbers (potential structuring)
    if amount % 10000 == 0 and amount >= 10000:
        risk_score += 0.2
        risk_factors.append(f"Round number amount: {amount:,.2f} (potential structuring)")
        details["round_number"] = True
    elif amount % 1000 == 0 and amount >= 1000:
        risk_score += 0.1
        risk_factors.append(f"Round number amount: {amount:,.2f}")
        details["round_number"] = True
    
    # Risk factor 3: Just below reporting threshold (99,999 to avoid 100k reporting)
    if 99000 <= eur_amount < 100000:
        risk_score += 0.25
        risk_factors.append(f"Amount just below reporting threshold: {amount:,.2f}")
        details["threshold_avoidance"] = True
    
    # Normalize risk score to 0.0-1.0
    risk_score = min(risk_score, 1.0)
    
    return {
        "risk_score": round(risk_score, 3),
        "risk_factors": risk_factors,
        "details": details,
        "eur_equivalent": round(eur_amount, 2)
    }


def verifier_pays_risque(country_code: Optional[str] = None, country_name: Optional[str] = None, 
                        bic: Optional[str] = None) -> Dict[str, Any]:
    """Check if country/jurisdiction is high-risk.
    
    Args:
        country_code: ISO country code (e.g., "AF", "IR")
        country_name: Country name
        bic: BIC code (contains country code)
        
    Returns:
        Dict with is_high_risk, risk_score, and details
    """
    risk_score = 0.0
    risk_factors = []
    is_high_risk = False
    
    # Extract country code from BIC if provided
    if bic and len(bic) >= 6:
        bic_country = bic[4:6]
        if bic_country in HIGH_RISK_COUNTRIES:
            is_high_risk = True
            risk_score = 0.5
            risk_factors.append(f"High-risk country in BIC: {bic_country}")
    
    # Check country code
    if country_code:
        if country_code.upper() in HIGH_RISK_COUNTRIES:
            is_high_risk = True
            risk_score = max(risk_score, 0.5)
            risk_factors.append(f"High-risk country code: {country_code}")
    
    # Check country name
    if country_name:
        country_lower = country_name.lower()
        for risk_country in HIGH_RISK_COUNTRY_NAMES:
            if risk_country in country_lower:
                is_high_risk = True
                risk_score = max(risk_score, 0.4)
                risk_factors.append(f"High-risk country name detected: {country_name}")
                break
    
    return {
        "is_high_risk": is_high_risk,
        "risk_score": round(risk_score, 3),
        "risk_factors": risk_factors,
        "country_code": country_code,
        "country_name": country_name
    }


def verifier_pep_sanctions(name: str, entity_type: str = "person") -> Dict[str, Any]:
    """Check if name matches PEP or sanctioned entities.
    
    Args:
        name: Name to check
        entity_type: "person" or "organization"
        
    Returns:
        Dict with is_pep, is_sanctioned, risk_score, and matches
    """
    risk_score = 0.0
    risk_factors = []
    is_pep = False
    is_sanctioned = False
    matches = []
    
    name_lower = name.lower()
    
    # Check for PEP keywords
    for keyword in PEP_KEYWORDS:
        if keyword in name_lower:
            is_pep = True
            risk_score += 0.3
            matches.append(f"PEP keyword: {keyword}")
            risk_factors.append(f"Potential PEP: {keyword} detected in name")
    
    # Check for sanctioned entity keywords
    for keyword in SANCTIONED_ENTITIES:
        if keyword in name_lower:
            is_sanctioned = True
            risk_score += 0.5
            matches.append(f"Sanctioned entity keyword: {keyword}")
            risk_factors.append(f"Potential sanctioned entity: {keyword} detected")
    
    # Normalize risk score
    risk_score = min(risk_score, 1.0)
    
    return {
        "is_pep": is_pep,
        "is_sanctioned": is_sanctioned,
        "risk_score": round(risk_score, 3),
        "risk_factors": risk_factors,
        "matches": matches
    }


def analyser_patternes_suspects(
    amount: float,
    reference: str,
    execution_date: Optional[str] = None,
    previous_transactions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Analyze transaction patterns for suspicious activity.
    
    Checks for:
    - Rapid succession of transactions (potential structuring)
    - Unusual timing (weekends, holidays)
    - Repeated round numbers
    - Unusual reference patterns
    
    Args:
        amount: Transaction amount
        reference: Transaction reference
        execution_date: Execution date (YYYY-MM-DD)
        previous_transactions: List of previous transactions (for pattern detection)
        
    Returns:
        Dict with risk_score, risk_factors, and pattern_details
    """
    risk_score = 0.0
    risk_factors = []
    pattern_details = {}
    
    # Pattern 1: Unusual timing
    if execution_date:
        try:
            dt = datetime.strptime(execution_date, "%Y-%m-%d")
            weekday = dt.weekday()
            # Weekend transactions (Saturday=5, Sunday=6)
            if weekday >= 5:
                risk_score += 0.1
                risk_factors.append(f"Transaction on weekend: {execution_date}")
                pattern_details["weekend_transaction"] = True
        except ValueError:
            pass
    
    # Pattern 2: Rapid succession (if previous transactions provided)
    if previous_transactions:
        recent_count = 0
        for tx in previous_transactions:
            tx_date = tx.get("date", "")
            if tx_date:
                try:
                    tx_dt = datetime.strptime(tx_date, "%Y-%m-%d")
                    if execution_date:
                        exec_dt = datetime.strptime(execution_date, "%Y-%m-%d")
                        if (exec_dt - tx_dt).days <= 1:
                            recent_count += 1
                except ValueError:
                    pass
        
        if recent_count >= 3:
            risk_score += 0.3
            risk_factors.append(f"Rapid succession: {recent_count} transactions in 24h")
            pattern_details["rapid_succession"] = True
        elif recent_count >= 2:
            risk_score += 0.15
            risk_factors.append(f"Multiple transactions in short period: {recent_count}")
            pattern_details["rapid_succession"] = True
    
    # Pattern 3: Unusual reference patterns
    if reference:
        # Check for sequential references (potential structuring)
        if re.match(r'^[A-Z]+\d{6,}$', reference):
            # Extract number part
            num_part = re.search(r'\d+', reference)
            if num_part:
                num = int(num_part.group())
                # Check if it's a round number or sequential
                if num % 100 == 0:
                    risk_score += 0.1
                    risk_factors.append("Sequential or round reference number")
                    pattern_details["sequential_reference"] = True
    
    # Pattern 4: Amount just below threshold (already checked in amount risk, but flag here too)
    if 99000 <= amount < 100000:
        risk_score += 0.2
        risk_factors.append("Amount pattern: Just below reporting threshold")
        pattern_details["threshold_avoidance"] = True
    
    # Normalize risk score
    risk_score = min(risk_score, 1.0)
    
    return {
        "risk_score": round(risk_score, 3),
        "risk_factors": risk_factors,
        "pattern_details": pattern_details
    }


def evaluer_risque_message(
    message_type: str,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    debtor_name: Optional[str] = None,
    creditor_name: Optional[str] = None,
    debtor_country: Optional[str] = None,
    creditor_country: Optional[str] = None,
    debtor_bic: Optional[str] = None,
    creditor_bic: Optional[str] = None,
    reference: Optional[str] = None,
    execution_date: Optional[str] = None,
    missing_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Comprehensive risk assessment for a financial message.
    
    Combines all risk factors into an overall risk score and matrix.
    
    Args:
        message_type: Message type (e.g., "MT103", "pacs.008")
        amount: Transaction amount
        currency: Currency code
        debtor_name: Debtor name
        creditor_name: Creditor name
        debtor_country: Debtor country code
        creditor_country: Creditor country code
        debtor_bic: Debtor BIC
        creditor_bic: Creditor BIC
        reference: Transaction reference
        execution_date: Execution date
        missing_fields: List of missing required fields
        
    Returns:
        Dict with overall risk assessment including scores, factors, and recommendations
    """
    risk_matrix = {}
    all_risk_factors = []
    recommendations = []
    
    # 1. Amount risk
    if amount is not None:
        amount_risk = calculer_score_risque_montant(amount, currency or "EUR")
        risk_matrix["amount"] = amount_risk["risk_score"]
        all_risk_factors.extend(amount_risk["risk_factors"])
    
    # 2. Country risk
    debtor_country_risk = verifier_pays_risque(debtor_country, bic=debtor_bic)
    creditor_country_risk = verifier_pays_risque(creditor_country, bic=creditor_bic)
    risk_matrix["debtor_country"] = debtor_country_risk["risk_score"]
    risk_matrix["creditor_country"] = creditor_country_risk["risk_score"]
    all_risk_factors.extend(debtor_country_risk["risk_factors"])
    all_risk_factors.extend(creditor_country_risk["risk_factors"])
    
    # 3. PEP/Sanctions risk
    if debtor_name:
        debtor_pep = verifier_pep_sanctions(debtor_name)
        risk_matrix["debtor_pep"] = debtor_pep["risk_score"]
        all_risk_factors.extend(debtor_pep["risk_factors"])
        if debtor_pep["is_sanctioned"]:
            recommendations.append("URGENT: Debtor may be on sanctions list - block transaction")
        elif debtor_pep["is_pep"]:
            recommendations.append("Enhanced due diligence required for debtor (PEP)")
    
    if creditor_name:
        creditor_pep = verifier_pep_sanctions(creditor_name)
        risk_matrix["creditor_pep"] = creditor_pep["risk_score"]
        all_risk_factors.extend(creditor_pep["risk_factors"])
        if creditor_pep["is_sanctioned"]:
            recommendations.append("URGENT: Creditor may be on sanctions list - block transaction")
        elif creditor_pep["is_pep"]:
            recommendations.append("Enhanced due diligence required for creditor (PEP)")
    
    # 4. Pattern analysis
    if amount is not None:
        pattern_risk = analyser_patternes_suspects(amount, reference or "", execution_date)
        risk_matrix["patterns"] = pattern_risk["risk_score"]
        all_risk_factors.extend(pattern_risk["risk_factors"])
    
    # 5. Data quality risk
    data_quality_score = 0.0
    if missing_fields:
        data_quality_score = len(missing_fields) * 0.1
        all_risk_factors.append(f"Missing required fields: {', '.join(missing_fields)}")
        recommendations.append("Complete missing fields before processing")
    risk_matrix["data_quality"] = min(data_quality_score, 1.0)
    
    # Calculate overall risk score (weighted average)
    if risk_matrix:
        overall_score = sum(risk_matrix.values()) / len(risk_matrix)
    else:
        overall_score = 0.0
    
    # Determine risk level
    if overall_score >= 0.7:
        risk_level = "CRITICAL"
        is_suspect = True
        recommendations.insert(0, "BLOCK TRANSACTION - High risk detected")
    elif overall_score >= 0.5:
        risk_level = "HIGH"
        is_suspect = True
        recommendations.insert(0, "REVIEW REQUIRED - Elevated risk")
    elif overall_score >= 0.3:
        risk_level = "MEDIUM"
        is_suspect = False
        recommendations.insert(0, "Enhanced monitoring recommended")
    else:
        risk_level = "LOW"
        is_suspect = False
    
    return {
        "overall_risk_score": round(overall_score, 3),
        "risk_level": risk_level,
        "risk_factors": all_risk_factors,
        "risk_matrix": risk_matrix,
        "is_suspect": is_suspect,
        "recommendations": recommendations
    }


# ============================================================================
# RISK ASSESSMENT AGENT
# ============================================================================

agent_5_risk = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1500),
    system_prompt=(
        "Vous êtes un expert en évaluation des risques financiers et conformité AML/KYC.\n\n"
        "RÈGLES CRITIQUES:\n"
        "1. TOUJOURS utiliser les outils de risque pour évaluer les messages\n"
        "2. Pour évaluer le risque d'un message: utilisez evaluer_risque_message\n"
        "3. Pour analyser le risque de montant: utilisez calculer_score_risque_montant\n"
        "4. Pour vérifier les pays à risque: utilisez verifier_pays_risque\n"
        "5. Pour vérifier PEP/sanctions: utilisez verifier_pep_sanctions\n"
        "6. Pour analyser les patterns suspects: utilisez analyser_patternes_suspects\n\n"
        "MATRICE DE RISQUE:\n"
        "- CRITICAL (≥0.7): Bloquer la transaction\n"
        "- HIGH (≥0.5): Révision requise\n"
        "- MEDIUM (≥0.3): Surveillance renforcée\n"
        "- LOW (<0.3): Risque acceptable\n\n"
        "FACTEURS DE RISQUE À VÉRIFIER:\n"
        "- Montants élevés ou suspects\n"
        "- Pays/juridictions à haut risque\n"
        "- Personnes politiquement exposées (PEP)\n"
        "- Entités sanctionnées\n"
        "- Patterns suspects (structuration, timing)\n"
        "- Données manquantes ou incohérentes\n\n"
        "Répondez avec un objet RiskScore structuré incluant:\n"
        "- Score de risque global (0.0-1.0) et niveau (LOW/MEDIUM/HIGH/CRITICAL)\n"
        "- Matrice de risque par catégorie\n"
        "- Facteurs de risque identifiés\n"
        "- Statut suspect (is_suspect: true/false)\n"
        "- Recommandations d'action"
    ),
    tools=[
        Tool(
            calculer_score_risque_montant,
            name="calculer_score_risque_montant",
            description="Calcule le score de risque basé sur le montant de la transaction. Fournissez amount (float) et optionnellement currency (défaut: EUR).",
        ),
        Tool(
            verifier_pays_risque,
            name="verifier_pays_risque",
            description="Vérifie si un pays/juridiction est à haut risque. Fournissez country_code (ISO code), country_name, ou bic (contient le code pays).",
        ),
        Tool(
            verifier_pep_sanctions,
            name="verifier_pep_sanctions",
            description="Vérifie si un nom correspond à une PEP ou entité sanctionnée. Fournissez name et optionnellement entity_type ('person' ou 'organization').",
        ),
        Tool(
            analyser_patternes_suspects,
            name="analyser_patternes_suspects",
            description="Analyse les patterns de transaction suspects. Fournissez amount, reference, execution_date (YYYY-MM-DD), et optionnellement previous_transactions (liste de dicts).",
        ),
        Tool(
            evaluer_risque_message,
            name="evaluer_risque_message",
            description="Évaluation complète du risque d'un message financier. Fournissez message_type et tous les champs disponibles (amount, currency, debtor_name, creditor_name, etc.).",
        ),
    ],
    output_type=RiskScore,
)


# ============================================================================
# EXAMPLES
# ============================================================================

async def exemple_evaluation_risque():
    """Exemple d'évaluation de risque pour un message."""
    print("🔍 Agent 5 Risk: Évaluation de Risque")
    print("=" * 70)
    
    # Example 1: High-risk transaction
    result1 = await agent_5_risk.run(
        "Évalue le risque de cette transaction:\n"
        "- Montant: 99,500 EUR\n"
        "- Débiteur: COMPAGNIE ABC (BIC: BANKIR12XXX)\n"
        "- Créancier: COMPAGNIE XYZ\n"
        "- Référence: PAY001234\n"
        "- Date d'exécution: 2024-01-15"
    )
    
    print("📊 Exemple 1: Transaction à risque élevé\n")
    print(result1.output)
    print("\n" + "=" * 70 + "\n")
    
    # Example 2: PEP transaction
    result2 = await agent_5_risk.run(
        "Évalue le risque de cette transaction:\n"
        "- Montant: 50,000 USD\n"
        "- Débiteur: MINISTER XYZ\n"
        "- Créancier: COMPAGNIE ABC\n"
        "- Pays créancier: AF (Afghanistan)\n"
        "- Référence: MIN001"
    )
    
    print("📊 Exemple 2: Transaction avec PEP\n")
    print(result2.output)
    print()


async def exemple_message_suspect():
    """Exemple d'identification d'un message suspect."""
    print("🚨 Agent 5 Risk: Message Suspect")
    print("=" * 70)
    
    result = await agent_5_risk.run(
        "Analyse ce message et détermine s'il est suspect:\n"
        "- Montant: 99,999 EUR (montant rond)\n"
        "- Débiteur: ORGANIZED CRIME SYNDICATE\n"
        "- Créancier: COMPAGNIE XYZ\n"
        "- Pays créancier: KP (Corée du Nord)\n"
        "- BIC créancier: BANKKP12XXX\n"
        "- Référence: TXN999999\n"
        "- Date: 2024-01-20 (samedi)"
    )
    
    print("📋 Analyse de message suspect:\n")
    print(result.output)
    print()


if __name__ == "__main__":
    asyncio.run(exemple_evaluation_risque())
    print("\n" + "=" * 70 + "\n")
    asyncio.run(exemple_message_suspect())

