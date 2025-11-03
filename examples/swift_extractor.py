"""
Module d'extraction avancée de messages SWIFT avec validation Pydantic.

Fournit des fonctions robustes pour parser et valider les messages SWIFT,
avec support des champs multi-lignes et validation stricte des formats.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ValidationError


class SwiftField32A(BaseModel):
    """Représente le champ :32A: (Date de valeur, devise, montant)."""
    value_date: str = Field(description="Date YYYYMMDD")
    currency: str = Field(description="Code devise ISO 3 lettres")
    amount: float = Field(description="Montant", gt=0)
    
    @field_validator("value_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        # Valider que c'est une date valide
        year = int(v[:4])
        month = int(v[4:6])
        day = int(v[6:8])
        if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError(f"Invalid date values: {v}")
        return v
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"Currency must be 3 letter ISO code, got: {v}")
        return v.upper()


class SwiftMT103Parsed(BaseModel):
    """Structure complète d'un message SWIFT MT103 parsé et validé."""
    
    # Champs obligatoires
    field_20: str = Field(description=":20: Référence du transfert")
    field_32A: SwiftField32A = Field(description=":32A: Date, devise, montant")
    field_50K: str = Field(description=":50K: Ordre donneur")
    field_59: str = Field(description=":59: Bénéficiaire")
    
    # Champs optionnels avec valeurs par défaut
    field_23B: str = Field(default="CRED", description=":23B: Code instruction")
    field_52A: Optional[str] = Field(default=None, description=":52A: BIC banque ordonnateur")
    field_56A: Optional[str] = Field(default=None, description=":56A: BIC banque intermédiaire")
    field_57A: Optional[str] = Field(default=None, description=":57A: BIC banque bénéficiaire")
    field_70: Optional[str] = Field(default=None, description=":70: Information pour bénéficiaire")
    field_71A: str = Field(default="OUR", description=":71A: Frais (OUR/SHA/BEN)")
    field_72: Optional[str] = Field(default=None, description=":72: Information banque à banque")
    
    # Champs extraits (IBAN, noms, etc.)
    ordering_customer_account: Optional[str] = Field(default=None, description="IBAN ordonnateur extrait")
    beneficiary_account: Optional[str] = Field(default=None, description="IBAN bénéficiaire extrait")
    
    @field_validator("field_71A")
    @classmethod
    def validate_charges(cls, v: str) -> str:
        valid = ["OUR", "SHA", "BEN"]
        if v not in valid:
            raise ValueError(f"Charges must be one of {valid}, got: {v}")
        return v
    
    @field_validator("field_52A", "field_56A", "field_57A")
    @classmethod
    def validate_bic(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()[:11]  # BIC max 11 caractères
        if len(v) not in [8, 11]:
            raise ValueError(f"BIC must be 8 or 11 characters, got: {len(v)}")
        return v


def extract_iban_from_text(text: str) -> Optional[str]:
    """Extrait un IBAN depuis un texte (format: 2 lettres + 2 chiffres + 12-34 caractères)."""
    # Pattern IBAN: 2 lettres pays + 2 chiffres + 12-34 alphanumériques
    pattern = r'\b([A-Z]{2}\d{2}[A-Z0-9\s]{12,34})\b'
    matches = re.findall(pattern, text)
    if matches:
        # Nettoyer (enlever espaces) et retourner le premier match
        iban = matches[0].replace(" ", "").replace("\n", "")
        if 15 <= len(iban) <= 34:  # Longueur IBAN valide
            return iban
    return None


def extract_bic_from_text(text: str) -> Optional[str]:
    """Extrait un BIC depuis un texte (8 ou 11 caractères alphanumériques)."""
    # Pattern BIC: 4 lettres + 2 lettres + 2 caractères (optionnel: 3 caractères)
    pattern = r'\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?)\b'
    matches = re.findall(pattern, text)
    if matches:
        return matches[0][0]  # Retourner le BIC complet
    return None


def parse_swift_field_32a(value: str) -> SwiftField32A:
    """
    Parse le champ :32A: (format: YYMMDD ou YYYYMMDD + 3 lettres + montant).
    
    Formats supportés:
    - YYMMDD + currency + amount (ex: 241215EUR15000.00)
    - YYYYMMDD + currency + amount (ex: 20241215EUR15000.00)
    """
    value = value.strip()
    
    # Déterminer si c'est un format à 6 chiffres (YYMMDD) ou 8 chiffres (YYYYMMDD)
    # On cherche le début de la devise (3 lettres majuscules)
    currency_match = re.search(r'([A-Z]{3})', value[6:])  # Chercher après les 6 premiers chiffres
    
    if not currency_match:
        raise ValueError(f"Cannot find currency code in :32A: {value}")
    
    currency_start = currency_match.start() + 6  # Position de début de la devise
    date_str = value[:currency_start]
    currency_str = currency_match.group(1)
    amount_str = value[currency_start + 3:].replace(",", ".").strip()
    
    # Convertir YYMMDD en YYYYMMDD si nécessaire
    if len(date_str) == 6:
        # Format YYMMDD - convertir en YYYYMMDD
        year = int(date_str[:2])
        # Supposer années 2000-2099 si YY < 50, sinon 1900-1999
        full_year = 2000 + year if year < 50 else 1900 + year
        date_str = f"{full_year}{date_str[2:]}"
    elif len(date_str) != 8:
        raise ValueError(f"Date must be 6 (YYMMDD) or 8 (YYYYMMDD) digits, got: {date_str} (length {len(date_str)})")
    
    if not amount_str:
        raise ValueError(f"Missing amount in :32A: {value}")
    
    try:
        amount = float(amount_str)
    except ValueError:
        raise ValueError(f"Invalid amount format in :32A: {amount_str}")
    
    return SwiftField32A(
        value_date=date_str,
        currency=currency_str,
        amount=amount
    )


def parse_swift_mt103_advanced(swift_text: str) -> SwiftMT103Parsed:
    """
    Parse un message SWIFT MT103 avec validation complète.
    
    Gère:
    - Tous les champs standard MT103
    - Champs multi-lignes
    - Extraction automatique d'IBAN et BIC
    - Validation stricte avec Pydantic
    """
    lines = [line.rstrip() for line in swift_text.split("\n")]
    
    data = {}
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # Pattern pour identifier les tags SWIFT (format :XX: ou :XXA:, :XXB:, etc.)
        tag_match = re.match(r'^:(\d{2}[A-Z]?):', line)
        if not tag_match:
            i += 1
            continue
        
        tag = tag_match.group(0)  # e.g. ":20:", ":32A:"
        tag_num = tag_match.group(1)  # e.g. "20", "32A"
        content_start = len(tag)
        
        # Extraire le contenu (peut être multi-lignes)
        content_lines = []
        current_line = line[content_start:].strip()
        if current_line:
            content_lines.append(current_line)
        
        # Lire les lignes suivantes jusqu'au prochain tag ou fin
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if next_line.startswith(":"):
                break
            if next_line:
                content_lines.append(next_line)
            i += 1
        
        full_content = "\n".join(content_lines)
        
        # Traitement selon le tag
        if tag_num == "20":
            data["field_20"] = full_content or "NONREF"
        
        elif tag_num == "23B":
            data["field_23B"] = full_content or "CRED"
        
        elif tag_num == "32A":
            data["field_32A"] = parse_swift_field_32a(full_content)
        
        elif tag_num.startswith("50"):
            data["field_50K"] = full_content
            # Extraire IBAN si présent
            iban = extract_iban_from_text(full_content)
            if iban:
                data["ordering_customer_account"] = iban
        
        elif tag_num == "52A":
            bic = extract_bic_from_text(full_content) or full_content[:11]
            data["field_52A"] = bic
        
        elif tag_num == "56A":
            bic = extract_bic_from_text(full_content) or full_content[:11]
            data["field_56A"] = bic
        
        elif tag_num == "57A":
            bic = extract_bic_from_text(full_content) or full_content[:11]
            data["field_57A"] = bic
        
        elif tag_num.startswith("59"):
            data["field_59"] = full_content
            # Extraire IBAN si présent
            iban = extract_iban_from_text(full_content)
            if iban:
                data["beneficiary_account"] = iban
        
        elif tag_num == "70":
            data["field_70"] = full_content
        
        elif tag_num == "71A":
            data["field_71A"] = full_content.strip() or "OUR"
        
        elif tag_num == "72":
            data["field_72"] = full_content
        
        # Ne pas incrémenter i ici car on l'a déjà fait dans la boucle while
    
    # Validation avec Pydantic
    try:
        return SwiftMT103Parsed(**data)
    except ValidationError as e:
        raise ValueError(f"Validation error: {e}") from e


def format_swift_mt103_from_parsed(parsed: SwiftMT103Parsed) -> str:
    """Reformate un message SWIFT MT103 depuis une structure parsée."""
    lines = [
        f":20:{parsed.field_20}",
        f":23B:{parsed.field_23B}",
        f":32A:{parsed.field_32A.value_date}{parsed.field_32A.currency}{parsed.field_32A.amount:.2f}",
    ]
    
    if parsed.field_52A:
        lines.append(f":52A:{parsed.field_52A}")
    
    lines.append(f":50K:/{parsed.field_50K}")
    
    if parsed.field_56A:
        lines.append(f":56A:{parsed.field_56A}")
    
    if parsed.field_57A:
        lines.append(f":57A:{parsed.field_57A}")
    
    lines.append(f":59:/{parsed.field_59}")
    
    if parsed.field_70:
        lines.append(f":70:{parsed.field_70}")
    
    lines.append(f":71A:{parsed.field_71A}")
    
    if parsed.field_72:
        lines.append(f":72:{parsed.field_72}")
    
    return "\n".join(lines)

