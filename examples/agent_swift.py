"""
Agent SWIFT: Génération et parsing de messages SWIFT structurés

Cet agent démontre l'utilisation de PydanticAI pour:
- Générer des messages SWIFT formatés depuis du texte naturel
- Extraire les données structurées d'un message SWIFT
- Valider la structure des messages SWIFT
"""

import asyncio
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model

# Imports relatifs pour les modules dans examples/
try:
    from .swift_models import SWIFTMT103Structured, MT103Field32A
    from .swift_extractor import (
        parse_swift_mt103_advanced,
        SwiftMT103Parsed,
        format_swift_mt103_from_parsed,
    )
except ImportError:
    # Fallback pour exécution directe
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from swift_models import SWIFTMT103Structured, MT103Field32A
    from swift_extractor import (
        parse_swift_mt103_advanced,
        SwiftMT103Parsed,
        format_swift_mt103_from_parsed,
    )

# Model settings for SWIFT generation (complex structured output)
swift_model_settings = ModelSettings(
    max_output_tokens=2000,  # Increased for SWIFT message generation
)


# Modèle pour un message SWIFT MT103 (Transfert de fonds)
class SWIFTMT103(BaseModel):
    """Message SWIFT MT103 - Transfert de fonds unique."""
    
    # En-tête
    message_type: str = Field(default="103", description="Type de message SWIFT (103)")
    sender_bic: str = Field(description="BIC de la banque émettrice (8 ou 11 caractères)")
    receiver_bic: str = Field(description="BIC de la banque réceptrice (8 ou 11 caractères)")
    
    # Champs obligatoires
    value_date: str = Field(description="Date de valeur au format YYYYMMDD")
    currency: str = Field(description="Code devise ISO (3 lettres)", min_length=3, max_length=3)
    amount: float = Field(description="Montant du transfert", gt=0)
    
    # Champs optionnels
    ordering_customer: str = Field(description="Données de l'ordre donneur (nom, adresse, compte)")
    beneficiary: str = Field(description="Données du bénéficiaire (nom, adresse, compte)")
    remittance_info: str | None = Field(default=None, description="Information pour le bénéficiaire")
    charges: str = Field(default="OUR", description="Frais: OUR, SHA, BEN")
    reference: str | None = Field(default=None, description="Référence du transfert")


class SWIFTMT940(BaseModel):
    """Message SWIFT MT940 - Relevé bancaire."""
    
    message_type: str = Field(default="940", description="Type de message SWIFT (940)")
    account_identification: str = Field(description="Identification du compte (IBAN)")
    statement_number: str = Field(description="Numéro de relevé")
    opening_balance_date: str = Field(description="Date de solde d'ouverture YYYYMMDD")
    opening_balance: float = Field(description="Solde d'ouverture")
    opening_balance_indicator: str = Field(description="C (Crédit) ou D (Débit)")
    currency: str = Field(description="Code devise ISO (3 lettres)")
    transactions: list[dict[str, str | float]] = Field(description="Liste des transactions")


# Agent pour génération de messages SWIFT
swift_generator = Agent(
    finance_model,
    model_settings=swift_model_settings,
    system_prompt=(
        "Vous êtes un expert en messages SWIFT bancaires. "
        "Votre rôle est de générer des messages SWIFT correctement formatés "
        "à partir de descriptions en langage naturel. "
        "Les messages SWIFT doivent être conformes aux standards internationaux. "
        "Pour les montants, utilisez toujours le format numérique avec 2 décimales. "
        "Les BIC doivent être valides (8 ou 11 caractères alphanumériques). "
        "Répondez en français mais générez les messages SWIFT au format standard.\n\n"
        "Vous disposez de 2000 tokens pour générer des messages SWIFT complets et détaillés."
    ),
)


# Agent pour parsing de messages SWIFT avec extraction structurée
swift_parser = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),
    system_prompt=(
        "Vous êtes un expert en parsing de messages SWIFT bancaires. "
        "Votre rôle est d'extraire précisément toutes les informations "
        "à partir de messages SWIFT formatés (MT103, MT940, etc.).\n\n"
        "Instructions importantes:\n"
        "- Identifiez TOUS les champs SWIFT présents (même optionnels)\n"
        "- Pour le champ :32A:, extrayez séparément la date (YYYYMMDD), devise (3 lettres), et montant\n"
        "- Pour les champs :50K: et :59:, conservez toutes les lignes (nom, adresse, compte)\n"
        "- Les dates doivent être au format YYYYMMDD\n"
        "- Les montants doivent être numériques avec décimales\n"
        "- Les BIC doivent être extraits des champs :52A:, :56A:, etc. si présents\n"
        "- Répondez en JSON structuré pour faciliter le parsing"
    ),
)


def format_swift_mt103(mt103: SWIFTMT103) -> str:
    """Formate un message SWIFT MT103 selon les standards."""
    lines = []
    
    # En-tête SWIFT
    lines.append(f":20:{mt103.reference or 'NONREF'}")
    lines.append(f":23B:CRED")
    lines.append(f":32A:{mt103.value_date}{mt103.currency}{mt103.amount:.2f}")
    lines.append(f":50K:/{mt103.ordering_customer}")
    lines.append(f":59:/{mt103.beneficiary}")
    
    if mt103.remittance_info:
        lines.append(f":70:{mt103.remittance_info}")
    
    lines.append(f":71A:{mt103.charges}")
    
    return "\n".join(lines)


class SWIFTExtractedMT103(BaseModel):
    """Structure extraite d'un message SWIFT MT103."""
    
    # Champ :20: - Référence du transfert
    reference: str = Field(description="Référence du transfert (:20:)")
    
    # Champ :23B: - Code instruction
    instruction_code: str = Field(default="CRED", description="Code instruction (:23B:)")
    
    # Champ :32A: - Date de valeur, devise, montant
    value_date: str = Field(description="Date de valeur YYYYMMDD")
    currency: str = Field(description="Code devise ISO 3 lettres")
    amount: float = Field(description="Montant", gt=0)
    
    # Champ :50K: ou :50A: - Ordre donneur (peut être multi-lignes)
    ordering_customer: str = Field(description="Données ordonnateur (:50K: ou :50A:)")
    ordering_customer_account: Optional[str] = Field(default=None, description="Compte ordonnateur (IBAN)")
    
    # Champ :52A:, :52D: - Banque ordonnateur (optionnel)
    ordering_bank_bic: Optional[str] = Field(default=None, description="BIC banque ordonnateur (:52A:)")
    ordering_bank_name: Optional[str] = Field(default=None, description="Nom banque ordonnateur (:52D:)")
    
    # Champ :56A:, :56D: - Banque intermédiaire (optionnel)
    intermediary_bank_bic: Optional[str] = Field(default=None, description="BIC banque intermédiaire (:56A:)")
    intermediary_bank_name: Optional[str] = Field(default=None, description="Nom banque intermédiaire (:56D:)")
    
    # Champ :57A:, :57D: - Banque bénéficiaire (optionnel)
    beneficiary_bank_bic: Optional[str] = Field(default=None, description="BIC banque bénéficiaire (:57A:)")
    beneficiary_bank_name: Optional[str] = Field(default=None, description="Nom banque bénéficiaire (:57D:)")
    
    # Champ :59: ou :59A: - Bénéficiaire (peut être multi-lignes)
    beneficiary: str = Field(description="Données bénéficiaire (:59: ou :59A:)")
    beneficiary_account: Optional[str] = Field(default=None, description="Compte bénéficiaire (IBAN)")
    
    # Champ :70: - Information pour le bénéficiaire (optionnel)
    remittance_info: Optional[str] = Field(default=None, description="Information bénéficiaire (:70:)")
    
    # Champ :71A: - Frais
    charges: str = Field(default="OUR", description="Frais: OUR/SHA/BEN (:71A:)")
    
    # Champ :72: - Information pour la banque (optionnel)
    bank_to_bank_info: Optional[str] = Field(default=None, description="Info banque à banque (:72:)")
    
    @field_validator("value_date")
    def validate_date(cls, v):
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        return v
    
    @field_validator("currency")
    def validate_currency(cls, v):
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"Currency must be 3 letter ISO code, got: {v}")
        return v.upper()
    
    @field_validator("charges")
    def validate_charges(cls, v):
        valid = ["OUR", "SHA", "BEN"]
        if v not in valid:
            raise ValueError(f"Charges must be one of {valid}, got: {v}")
        return v


def parse_swift_mt103(swift_text: str) -> SWIFTExtractedMT103:
    """
    Parse un message SWIFT MT103 et extrait tous les champs avec validation.
    
    Gère:
    - Champs multi-lignes (:50K:, :59:, etc.)
    - Champs optionnels
    - Extraction des BIC et noms de banques
    - Validation des formats (dates, devises, montants)
    """
    # Nettoyer le texte
    lines = [line.strip() for line in swift_text.strip().split("\n") if line.strip()]
    
    parsed_data = {
        "reference": "NONREF",
        "instruction_code": "CRED",
        "charges": "OUR",
    }
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Champ :20: - Référence
        if line.startswith(":20:"):
            parsed_data["reference"] = line[4:].strip()
        
        # Champ :23B: - Code instruction
        elif line.startswith(":23B:"):
            parsed_data["instruction_code"] = line[5:].strip()
        
        # Champ :32A: - Date, devise, montant (format: YYYYMMDD + 3 lettres + montant)
        elif line.startswith(":32A:"):
            value = line[5:].strip()
            if len(value) >= 11:
                parsed_data["value_date"] = value[:8]
                parsed_data["currency"] = value[8:11].upper()
                try:
                    parsed_data["amount"] = float(value[11:].replace(",", "."))
                except ValueError:
                    raise ValueError(f"Invalid amount format in :32A: {value[11:]}")
        
        # Champ :50K:, :50A:, :50F: - Ordre donneur (peut être multi-lignes)
        elif line.startswith(":50") and ":" in line:
            tag_end = line.index(":")
            tag = line[:tag_end+1]
            content_parts = [line[tag_end+1:].strip()]
            i += 1
            
            # Lire les lignes suivantes jusqu'au prochain tag
            while i < len(lines) and not lines[i].startswith(":"):
                if lines[i].strip():
                    content_parts.append(lines[i].strip())
                i += 1
            i -= 1  # Revenir en arrière car on a avancé trop loin
            
            full_content = "\n".join(content_parts)
            parsed_data["ordering_customer"] = full_content
            
            # Extraire le compte (IBAN) si présent
            iban_match = re.search(r'([A-Z]{2}\d{2}[A-Z0-9\s]{12,34})', full_content)
            if iban_match:
                parsed_data["ordering_customer_account"] = iban_match.group(1).replace(" ", "")
        
        # Champ :52A:, :52D: - Banque ordonnateur
        elif line.startswith(":52A:"):
            parsed_data["ordering_bank_bic"] = line[5:].strip()[:11]
        elif line.startswith(":52D:"):
            parsed_data["ordering_bank_name"] = line[5:].strip()
        
        # Champ :56A:, :56D: - Banque intermédiaire
        elif line.startswith(":56A:"):
            parsed_data["intermediary_bank_bic"] = line[5:].strip()[:11]
        elif line.startswith(":56D:"):
            parsed_data["intermediary_bank_name"] = line[5:].strip()
        
        # Champ :57A:, :57D: - Banque bénéficiaire
        elif line.startswith(":57A:"):
            parsed_data["beneficiary_bank_bic"] = line[5:].strip()[:11]
        elif line.startswith(":57D:"):
            parsed_data["beneficiary_bank_name"] = line[5:].strip()
        
        # Champ :59:, :59A: - Bénéficiaire (peut être multi-lignes)
        elif line.startswith(":59"):
            tag_end = line.index(":")
            tag = line[:tag_end+1]
            content_parts = [line[tag_end+1:].strip()]
            i += 1
            
            # Lire les lignes suivantes jusqu'au prochain tag
            while i < len(lines) and not lines[i].startswith(":"):
                if lines[i].strip():
                    content_parts.append(lines[i].strip())
                i += 1
            i -= 1
            
            full_content = "\n".join(content_parts)
            parsed_data["beneficiary"] = full_content
            
            # Extraire le compte (IBAN) si présent
            iban_match = re.search(r'([A-Z]{2}\d{2}[A-Z0-9\s]{12,34})', full_content)
            if iban_match:
                parsed_data["beneficiary_account"] = iban_match.group(1).replace(" ", "")
        
        # Champ :70: - Information pour bénéficiaire
        elif line.startswith(":70:"):
            content_parts = [line[4:].strip()]
            i += 1
            while i < len(lines) and not lines[i].startswith(":"):
                if lines[i].strip():
                    content_parts.append(lines[i].strip())
                i += 1
            i -= 1
            parsed_data["remittance_info"] = "\n".join(content_parts)
        
        # Champ :71A: - Frais
        elif line.startswith(":71A:"):
            parsed_data["charges"] = line[5:].strip()
        
        # Champ :72: - Information banque à banque
        elif line.startswith(":72:"):
            content_parts = [line[4:].strip()]
            i += 1
            while i < len(lines) and not lines[i].startswith(":"):
                if lines[i].strip():
                    content_parts.append(lines[i].strip())
                i += 1
            i -= 1
            parsed_data["bank_to_bank_info"] = "\n".join(content_parts)
        
        i += 1
    
    # Valider que les champs obligatoires sont présents
    required_fields = ["value_date", "currency", "amount", "ordering_customer", "beneficiary"]
    missing = [f for f in required_fields if f not in parsed_data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    return SWIFTExtractedMT103(**parsed_data)


async def exemple_generation_swift():
    """Exemple de génération d'un message SWIFT MT103."""
    print("📨 Agent SWIFT: Génération de message MT103")
    print("=" * 60)
    
    demande = """
    Je veux transférer 15 000 euros de mon compte à la BNP Paribas (BIC: BNPAFRPPXXX)
    vers le compte de Jean Dupont à la Société Générale (BIC: SOGEFRPPXXX)
    le 15 décembre 2024.
    
    Mon compte: FR76 3000 4000 0100 0000 0000 123
    Compte bénéficiaire: FR14 2004 1010 0505 0001 3M02 606
    Référence: INVOICE-2024-001
    Motif: Paiement facture décembre 2024
    Les frais sont à ma charge.
    """
    
    print(f"Demande:\n{demande}\n")
    
    prompt = f"""
    Génère un message SWIFT MT103 à partir de cette demande:
    {demande}
    
    Fournis les informations structurées suivantes:
    - BIC émetteur et récepteur
    - Date de valeur (format YYYYMMDD)
    - Devise et montant
    - Données ordonnateur et bénéficiaire
    - Référence et motif
    - Qui paie les frais (OUR = ordonnateur, SHA = partagé, BEN = bénéficiaire)
    """
    
    result = await swift_generator.run(prompt)
    
    print("✅ Message SWIFT généré:")
    print(result.output)
    print()
    
    # Extraire les données structurées depuis la réponse avec validation
    print("📊 Extraction des données structurées...")
    
    # D'abord, extraire le message SWIFT brut (sans les explications)
    swift_lines = []
    for line in result.output.split("\n"):
        if line.strip().startswith(":") and ":" in line:
            swift_lines.append(line.strip())
    
    if swift_lines:
        swift_message = "\n".join(swift_lines)
        print("Message SWIFT extrait:")
        print(swift_message)
        print()
        
        # Parser avec validation Pydantic avancée
        try:
            extracted = parse_swift_mt103_advanced(swift_message)
            print("✅ Données extraites et validées:")
            print(f"  Référence: {extracted.field_20}")
            print(f"  Date: {extracted.field_32A.value_date}")
            print(f"  Montant: {extracted.field_32A.amount:,.2f} {extracted.field_32A.currency}")
            print(f"  Ordonnateur: {extracted.field_50K[:50]}...")
            print(f"  Bénéficiaire: {extracted.field_59[:50]}...")
            print(f"  Frais: {extracted.field_71A}")
        except Exception as e:
            print(f"⚠️ Erreur de parsing structuré: {e}")
            # Fallback: extraction via LLM
            extraction = await swift_parser.run(
                f"Extrais les données structurées du message SWIFT suivant:\n{swift_message}"
            )
            print(extraction.output[:500])
    else:
        # Fallback si aucun format SWIFT détecté
        extraction = await swift_parser.run(
            f"Extrais les données structurées du message SWIFT suivant:\n{result.output}"
        )
        print(extraction.output[:500])


async def exemple_parsing_swift():
    """Exemple de parsing d'un message SWIFT existant."""
    print("\n🔍 Agent SWIFT: Parsing de message MT103")
    print("=" * 60)
    
    swift_message = """
:20:NONREF
:23B:CRED
:32A:241215EUR15000.00
:50K:/FR76300040000100000000000123
ORDRE DUPONT JEAN
RUE DE LA REPUBLIQUE 123
75001 PARIS FRANCE

:59:/FR1420041010050500013M02606
BENEFICIAIRE MARTIN PIERRE
AVENUE DES CHAMPS ELYSEES 456
75008 PARIS FRANCE

:70:Paiement facture décembre 2024
:71A:OUR
    """
    
    print("Message SWIFT à parser:\n")
    print(swift_message)
    print()
    
    result = await swift_parser.run(
        f"Parse ce message SWIFT MT103 et extrais toutes les informations:\n{swift_message}\n\n"
        "Fournis:\n- Type de message\n- Date de valeur\n- Montant et devise\n"
        "- Données ordonnateur\n- Données bénéficiaire\n- Référence et motif\n- Frais"
    )
    
    print("✅ Données extraites:")
    print(result.output)
    
    # Parser technique avec validation Pydantic avancée
    print("\n🔧 Parsing technique avec validation avancée:")
    try:
        # Utiliser le parser avancé
        parsed = parse_swift_mt103_advanced(swift_message)
        print("✅ Message SWIFT parsé et validé avec succès:")
        print(f"  Référence (:20:): {parsed.field_20}")
        print(f"  Code instruction (:23B:): {parsed.field_23B}")
        print(f"  Date de valeur: {parsed.field_32A.value_date}")
        print(f"  Devise: {parsed.field_32A.currency}")
        print(f"  Montant: {parsed.field_32A.amount:,.2f} {parsed.field_32A.currency}")
        print(f"  Ordonnateur (:50K:):\n    {parsed.field_50K.replace(chr(10), chr(10) + '    ')}")
        if parsed.ordering_customer_account:
            print(f"  → IBAN ordonnateur extrait: {parsed.ordering_customer_account}")
        if parsed.field_52A:
            print(f"  Banque ordonnateur (:52A:): {parsed.field_52A}")
        if parsed.field_56A:
            print(f"  Banque intermédiaire (:56A:): {parsed.field_56A}")
        if parsed.field_57A:
            print(f"  Banque bénéficiaire (:57A:): {parsed.field_57A}")
        print(f"  Bénéficiaire (:59:):\n    {parsed.field_59.replace(chr(10), chr(10) + '    ')}")
        if parsed.beneficiary_account:
            print(f"  → IBAN bénéficiaire extrait: {parsed.beneficiary_account}")
        if parsed.field_70:
            print(f"  Motif (:70:): {parsed.field_70}")
        print(f"  Frais (:71A:): {parsed.field_71A}")
        if parsed.field_72:
            print(f"  Info banque (:72:): {parsed.field_72}")
    except Exception as e:
        print(f"❌ Erreur lors du parsing: {e}")
        import traceback
        traceback.print_exc()


async def exemple_synthese_swift():
    """Exemple de synthèse d'un message SWIFT depuis plusieurs sources."""
    print("\n🔄 Agent SWIFT: Synthèse de message")
    print("=" * 60)
    
    contexte = """
    Informations de la transaction:
    - Virement international de 50 000 USD
    - De: ABC Bank New York (BIC: ABCDUS33XXX) vers XYZ Bank Paris (BIC: XYZDFRPPXXX)
    - Date: 20 janvier 2025
    - Compte ordonnateur: US64 SVBKUS6SXXX 123456789
    - Compte bénéficiaire: FR76 3000 4000 0100 0000 0000 456
    - Référence client: TXN-2025-001
    - Motif: Paiement services consultance Q1 2025
    - Frais partagés (SHA)
    """
    
    print(f"Contexte:\n{contexte}\n")
    
    result = await swift_generator.run(
        f"Génère un message SWIFT MT103 complet et correctement formaté:\n{contexte}\n\n"
        "Assure-toi que:\n- Les BIC sont au bon format\n- La date est au format YYYYMMDD\n"
        "- Le montant a 2 décimales\n- Les comptes incluent le code pays\n"
        "- Tous les champs obligatoires sont présents"
    )
    
    print("✅ Message SWIFT synthétisé:")
    swift_msg = result.output
    
    # Extraire juste le format SWIFT si l'agent a ajouté des explications
    swift_lines = []
    for line in swift_msg.split("\n"):
        if line.strip().startswith(":"):
            swift_lines.append(line.strip())
    
    if swift_lines:
        print("\n".join(swift_lines))
    else:
        print(swift_msg)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EXEMPLES D'AGENTS SWIFT AVEC PYDANTICAI")
    print("=" * 60 + "\n")
    
    asyncio.run(exemple_generation_swift())
    asyncio.run(exemple_parsing_swift())
    asyncio.run(exemple_synthese_swift())
    
    print("\n" + "=" * 60)
    print("✅ Tous les exemples terminés!")
    print("=" * 60)

