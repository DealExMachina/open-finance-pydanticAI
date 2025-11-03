"""
Agent SWIFT: Génération et parsing de messages SWIFT structurés

Cet agent démontre l'utilisation de PydanticAI pour:
- Générer des messages SWIFT formatés depuis du texte naturel
- Extraire les données structurées d'un message SWIFT
- Valider la structure des messages SWIFT
"""

import asyncio
import re
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, ModelSettings

from app.models import finance_model

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


# Agent pour parsing de messages SWIFT
swift_parser = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=1500),  # Sufficient for structured extraction
    system_prompt=(
        "Vous êtes un expert en parsing de messages SWIFT. "
        "Votre rôle est d'extraire les informations structurées "
        "à partir de messages SWIFT formatés. "
        "Identifiez tous les champs du message et extrayez les données correspondantes. "
        "Répondez en français avec les données extraites de manière structurée."
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


def parse_swift_mt103(swift_text: str) -> dict:
    """Parse un message SWIFT MT103 et extrait les champs."""
    parsed = {}
    
    # Patterns SWIFT
    patterns = {
        ":20:": "reference",
        ":23B:": "instruction_code",
        ":32A:": "value_date_currency_amount",
        ":50K:": "ordering_customer",
        ":59:": "beneficiary",
        ":70:": "remittance_info",
        ":71A:": "charges",
    }
    
    for line in swift_text.split("\n"):
        for tag, field_name in patterns.items():
            if line.startswith(tag):
                value = line[len(tag):].strip()
                parsed[field_name] = value
                
                # Parser le champ :32A: (date + devise + montant)
                if field_name == "value_date_currency_amount" and len(value) >= 11:
                    parsed["value_date"] = value[:8]
                    parsed["currency"] = value[8:11]
                    parsed["amount"] = float(value[11:])
                break
    
    return parsed


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
    
    # Extraire les données structurées depuis la réponse
    print("📊 Extraction des données structurées...")
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
    
    # Parser technique
    print("\n🔧 Parsing technique (regex):")
    parsed = parse_swift_mt103(swift_message)
    for key, value in parsed.items():
        print(f"  {key}: {value}")


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

