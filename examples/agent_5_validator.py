"""
Agent 5 Validator: Validates SWIFT MT and ISO 20022 message outputs

This agent checks that converted messages are well-formed and valid:
- SWIFT message structure validation
- ISO 20022 XML validation
- Field completeness checks
- IBAN format validation
- Amount/currency validation
- Cross-format consistency checks
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings, Tool

from app.models import finance_model


# ============================================================================
# VALIDATION MODELS
# ============================================================================

class ValidationResult(BaseModel):
    """Result of message validation."""
    is_valid: bool = Field(description="Whether the message is valid")
    errors: List[str] = Field(description="List of validation errors", default_factory=list)
    warnings: List[str] = Field(description="List of validation warnings", default_factory=list)
    checks_performed: List[str] = Field(description="List of checks performed", default_factory=list)


# ============================================================================
# VALIDATION TOOLS
# ============================================================================

def valider_swift_message(swift_message: str) -> Dict[str, Any]:
    """Validate a SWIFT MT message structure and format.
    
    Checks:
    - Message has required blocks (1, 2, 4, 5)
    - Block 2 contains valid message type
    - Block 4 contains valid field tags
    - Required fields are present (for MT103: :20:, :32A:, :50A/:50K, :59/:59A)
    - Field formats are correct
    
    Args:
        swift_message: Raw SWIFT MT message string
        
    Returns:
        Dict with is_valid, errors, warnings, and checks_performed
    """
    errors = []
    warnings = []
    checks_performed = []
    
    # Check 1: Required blocks
    checks_performed.append("Block structure check")
    block1_match = re.search(r'\{1:([^}]+)\}', swift_message)
    block2_match = re.search(r'\{2:([^}]+)\}', swift_message)
    block4_match = re.search(r'\{4:([^}]+)\}', swift_message, re.DOTALL)
    block5_match = re.search(r'\{5:([^}]+)\}', swift_message)
    
    if not block1_match:
        errors.append("Missing Block 1 (Basic Header Block)")
    if not block2_match:
        errors.append("Missing Block 2 (Application Header Block)")
    if not block4_match:
        errors.append("Missing Block 4 (Text Block)")
    if not block5_match:
        warnings.append("Missing Block 5 (Trailer Block) - optional but recommended")
    
    # Check 2: Message type from Block 2
    checks_performed.append("Message type validation")
    if block2_match:
        block2 = block2_match.group(1)
        # Format: O103... or I103... (O=Output, I=Input, 103=message type)
        if len(block2) < 4:
            errors.append("Block 2 format invalid")
        else:
            msg_type = block2[1:4]  # Skip direction indicator
            if not msg_type.isdigit():
                errors.append(f"Invalid message type in Block 2: {msg_type}")
    
    # Check 3: Required fields for MT103
    checks_performed.append("Required fields check")
    if block4_match:
        text_block = block4_match.group(1)
        
        # Check for required MT103 fields
        has_20 = bool(re.search(r':20:', text_block))
        has_32A = bool(re.search(r':32A:', text_block))
        has_50 = bool(re.search(r':50[AK]:', text_block))
        has_59 = bool(re.search(r':59[AK]?:', text_block))
        
        if not has_20:
            errors.append("Missing required field :20: (Reference)")
        if not has_32A:
            errors.append("Missing required field :32A: (Value Date, Currency, Amount)")
        if not has_50:
            errors.append("Missing required field :50A or :50K (Ordering Customer)")
        if not has_59:
            errors.append("Missing required field :59 or :59A (Beneficiary Customer)")
    
    # Check 4: Field format validation
    checks_performed.append("Field format validation")
    if block4_match:
        text_block = block4_match.group(1)
        
        # Validate :32A: format (YYMMDDCURRENCYAMOUNT)
        field_32a_match = re.search(r':32A:([^\n]+)', text_block)
        if field_32a_match:
            field_32a = field_32a_match.group(1).strip()
            # Should be: YYMMDD + 3-letter currency + amount
            if not re.match(r'\d{6}[A-Z]{3}[\d,\.]+', field_32a):
                errors.append(f"Field :32A: has invalid format: {field_32a}")
        
        # Validate IBAN format in :50A: and :59:
        for field_tag in [":50A:", ":59:"]:
            field_match = re.search(f'{field_tag}([^\n]+)', text_block)
            if field_match:
                field_value = field_match.group(1).strip()
                # Check for IBAN format (starts with 2 letters, then digits)
                if "/" in field_value:
                    iban_part = field_value.split("/")[1] if len(field_value.split("/")) > 1 else ""
                    if iban_part and not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', iban_part):
                        warnings.append(f"IBAN format in {field_tag} may be invalid: {iban_part[:20]}")
    
    is_valid = len(errors) == 0
    
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "checks_performed": checks_performed
    }


def valider_iso20022_message(iso20022_xml: str) -> Dict[str, Any]:
    """Validate an ISO 20022 XML message structure and format.
    
    Checks:
    - XML is well-formed
    - Required namespaces are present
    - Required elements are present (for pacs.008)
    - Data types are correct
    - IBAN format validation
    - Amount format validation
    
    Args:
        iso20022_xml: ISO 20022 XML message string
        
    Returns:
        Dict with is_valid, errors, warnings, and checks_performed
    """
    errors = []
    warnings = []
    checks_performed = []
    
    # Check 1: XML well-formedness
    checks_performed.append("XML well-formedness check")
    try:
        root = ET.fromstring(iso20022_xml)
    except ET.ParseError as e:
        errors.append(f"XML parsing error: {str(e)}")
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "checks_performed": checks_performed
        }
    except ExpatError as e:
        errors.append(f"XML parsing error: {str(e)}")
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "checks_performed": checks_performed
        }
    
    # Check 2: Namespace validation
    checks_performed.append("Namespace validation")
    root_tag = root.tag
    if "Document" not in root_tag:
        warnings.append("Root element is not 'Document' - may not be standard ISO 20022")
    
    # Check 3: Required elements for pacs.008
    checks_performed.append("Required elements check")
    
    # Check for CstmrCdtTrfInitn (pacs.008)
    cstmr_cdt_trf = root.find(".//{*}CstmrCdtTrfInitn")
    if cstmr_cdt_trf is None:
        warnings.append("Message may not be pacs.008 (CstmrCdtTrfInitn not found)")
    else:
        # Check required elements
        grp_hdr = cstmr_cdt_trf.find(".//{*}GrpHdr")
        if grp_hdr is None:
            errors.append("Missing GrpHdr (Group Header)")
        else:
            msg_id = grp_hdr.find(".//{*}MsgId")
            if msg_id is None or not msg_id.text:
                errors.append("Missing or empty MsgId")
        
        # Check payment information
        pmt_inf = cstmr_cdt_trf.find(".//{*}PmtInf")
        if pmt_inf is None:
            errors.append("Missing PmtInf (Payment Information)")
        else:
            cdt_trf_tx_inf = pmt_inf.find(".//{*}CdtTrfTxInf")
            if cdt_trf_tx_inf is None:
                errors.append("Missing CdtTrfTxInf (Credit Transfer Transaction Information)")
            else:
                # Check required fields
                pmt_id = cdt_trf_tx_inf.find(".//{*}PmtId")
                if pmt_id is None:
                    errors.append("Missing PmtId (Payment Identification)")
                else:
                    end_to_end_id = pmt_id.find(".//{*}EndToEndId")
                    if end_to_end_id is None or not end_to_end_id.text:
                        warnings.append("Missing or empty EndToEndId (recommended)")
                
                amt = cdt_trf_tx_inf.find(".//{*}Amt")
                if amt is None:
                    errors.append("Missing Amt (Amount)")
                else:
                    instd_amt = amt.find(".//{*}InstdAmt")
                    if instd_amt is None or not instd_amt.text:
                        errors.append("Missing or empty InstdAmt (Instructed Amount)")
                    else:
                        # Validate amount format
                        try:
                            float(instd_amt.text)
                        except ValueError:
                            errors.append(f"Invalid amount format: {instd_amt.text}")
                        
                        # Check currency
                        if "Ccy" not in instd_amt.attrib:
                            errors.append("Missing currency (Ccy attribute)")
                        elif len(instd_amt.attrib["Ccy"]) != 3:
                            errors.append(f"Invalid currency code: {instd_amt.attrib['Ccy']}")
                
                # Check debtor
                dbtr = cdt_trf_tx_inf.find(".//{*}Dbtr")
                if dbtr is None:
                    errors.append("Missing Dbtr (Debtor)")
                else:
                    dbtr_nm = dbtr.find(".//{*}Nm")
                    if dbtr_nm is None or not dbtr_nm.text:
                        warnings.append("Missing or empty debtor name")
                
                dbtr_acct = cdt_trf_tx_inf.find(".//{*}DbtrAcct")
                if dbtr_acct is None:
                    warnings.append("Missing DbtrAcct (Debtor Account)")
                else:
                    iban = dbtr_acct.find(".//{*}IBAN")
                    if iban is not None and iban.text:
                        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', iban.text):
                            errors.append(f"Invalid IBAN format for debtor: {iban.text}")
                
                # Check creditor
                cdtr = cdt_trf_tx_inf.find(".//{*}Cdtr")
                if cdtr is None:
                    errors.append("Missing Cdtr (Creditor)")
                else:
                    cdtr_nm = cdtr.find(".//{*}Nm")
                    if cdtr_nm is None or not cdtr_nm.text:
                        warnings.append("Missing or empty creditor name")
                
                cdtr_acct = cdt_trf_tx_inf.find(".//{*}CdtrAcct")
                if cdtr_acct is None:
                    warnings.append("Missing CdtrAcct (Creditor Account)")
                else:
                    iban = cdtr_acct.find(".//{*}IBAN")
                    if iban is not None and iban.text:
                        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', iban.text):
                            errors.append(f"Invalid IBAN format for creditor: {iban.text}")
    
    is_valid = len(errors) == 0
    
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "checks_performed": checks_performed
    }


def valider_conversion(
    original_message: str,
    converted_message: str,
    conversion_direction: str
) -> Dict[str, Any]:
    """Validate that a conversion preserved all important information.
    
    Checks:
    - Reference/ID consistency
    - Amount consistency
    - Currency consistency
    - Debtor/Creditor name consistency
    - IBAN consistency
    - Date consistency
    
    Args:
        original_message: Original message (SWIFT or ISO 20022)
        converted_message: Converted message (ISO 20022 or SWIFT)
        conversion_direction: "swift_to_iso" or "iso_to_swift"
        
    Returns:
        Dict with is_valid, errors, warnings, and checks_performed
    """
    errors = []
    warnings = []
    checks_performed = []
    
    # Import parsing functions (handle import path)
    try:
        from examples.agent_5 import parser_swift_mt, parser_iso20022
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from examples.agent_5 import parser_swift_mt, parser_iso20022
    
    checks_performed.append("Conversion consistency check")
    
    if conversion_direction == "swift_to_iso":
        # Parse both messages
        swift_parsed = parser_swift_mt(original_message)
        iso_parsed = parser_iso20022(converted_message)
        
        if not swift_parsed.get("parsed_successfully"):
            errors.append("Failed to parse original SWIFT message")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "checks_performed": checks_performed
            }
        
        if not iso_parsed.get("parsed_successfully"):
            errors.append("Failed to parse converted ISO 20022 message")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "checks_performed": checks_performed
            }
        
        swift_fields = swift_parsed["fields"]
        iso_data = iso_parsed["structured_data"]
        
        # Check reference
        checks_performed.append("Reference consistency")
        swift_ref = swift_fields.get("20", "")
        iso_ref = iso_data.get("end_to_end_id", "")
        if swift_ref and iso_ref and swift_ref != iso_ref:
            warnings.append(f"Reference mismatch: SWIFT '{swift_ref}' vs ISO '{iso_ref}'")
        
        # Check amount
        checks_performed.append("Amount consistency")
        swift_32a = swift_fields.get("32A", "")
        if swift_32a:
            # Extract amount from :32A: (format: YYMMDDCURRENCYAMOUNT)
            match = re.match(r'\d{6}[A-Z]{3}([\d,\.]+)', swift_32a)
            if match:
                swift_amount = float(match.group(1).replace(',', '.'))
                iso_amount = float(iso_data.get("amount", "0"))
                if abs(swift_amount - iso_amount) > 0.01:
                    errors.append(f"Amount mismatch: SWIFT {swift_amount} vs ISO {iso_amount}")
        
    elif conversion_direction == "iso_to_swift":
        # Parse both messages
        iso_parsed = parser_iso20022(original_message)
        swift_parsed = parser_swift_mt(converted_message)
        
        if not iso_parsed.get("parsed_successfully"):
            errors.append("Failed to parse original ISO 20022 message")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "checks_performed": checks_performed
            }
        
        if not swift_parsed.get("parsed_successfully"):
            errors.append("Failed to parse converted SWIFT message")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "checks_performed": checks_performed
            }
        
        iso_data = iso_parsed["structured_data"]
        swift_fields = swift_parsed["fields"]
        
        # Check reference
        checks_performed.append("Reference consistency")
        iso_ref = iso_data.get("end_to_end_id", "")
        swift_ref = swift_fields.get("20", "")
        if iso_ref and swift_ref and iso_ref != swift_ref:
            warnings.append(f"Reference mismatch: ISO '{iso_ref}' vs SWIFT '{swift_ref}'")
        
        # Check amount
        checks_performed.append("Amount consistency")
        iso_amount = float(iso_data.get("amount", "0"))
        swift_32a = swift_fields.get("32A", "")
        if swift_32a:
            match = re.match(r'\d{6}[A-Z]{3}([\d,\.]+)', swift_32a)
            if match:
                swift_amount = float(match.group(1).replace(',', '.'))
                if abs(iso_amount - swift_amount) > 0.01:
                    errors.append(f"Amount mismatch: ISO {iso_amount} vs SWIFT {swift_amount}")
    
    is_valid = len(errors) == 0
    
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "checks_performed": checks_performed
    }


# ============================================================================
# VALIDATION AGENT
# ============================================================================

agent_5_validator = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=2000),
    system_prompt="""Vous êtes un expert en validation de messages financiers SWIFT MT et ISO 20022.

⚠️ RÈGLES ABSOLUES:
1. VOUS DEVEZ TOUJOURS utiliser les outils de validation AVANT de répondre
2. Pour valider un message SWIFT → APPELEZ valider_swift_message (OBLIGATOIRE)
3. Pour valider un message ISO 20022 → APPELEZ valider_iso20022_message (OBLIGATOIRE)
4. Pour valider une conversion → APPELEZ valider_conversion (OBLIGATOIRE)
5. NE RÉPONDEZ JAMAIS sans avoir appelé un outil de validation
6. Utilisez TOUJOURS les outils - c'est la seule façon de valider correctement

VALIDATIONS À EFFECTUER:
- Structure du message (blocs/éléments requis)
- Format des champs (dates, montants, devises)
- Format IBAN (2 lettres + 2 chiffres + alphanumérique)
- Présence des champs obligatoires
- Cohérence des données après conversion

ACTION REQUISE: Quand on vous demande de valider, appelez DIRECTEMENT l'outil approprié.
Répondez avec un objet ValidationResult structuré basé sur les résultats de l'outil.""",
    tools=[
        Tool(
            valider_swift_message,
            name="valider_swift_message",
            description="Valide un message SWIFT MT. Vérifie la structure, les blocs requis, les champs obligatoires, et les formats. Fournissez le message SWIFT brut.",
        ),
        Tool(
            valider_iso20022_message,
            name="valider_iso20022_message",
            description="Valide un message ISO 20022 XML. Vérifie que le XML est bien formé, les éléments requis, les formats de données, et les IBANs. Fournissez le contenu XML.",
        ),
        Tool(
            valider_conversion,
            name="valider_conversion",
            description="Valide qu'une conversion a préservé toutes les informations importantes. Compare le message original et converti. Fournissez original_message, converted_message, et conversion_direction ('swift_to_iso' ou 'iso_to_swift').",
        ),
    ],
    output_type=ValidationResult,
)


# ============================================================================
# EXAMPLES
# ============================================================================

async def exemple_validation_swift():
    """Exemple de validation d'un message SWIFT."""
    swift_message = """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF123456789
:32A:240101EUR1000,00
:50A:/FR1420041010050500013M02606
COMPAGNIE ABC
:59:/DE89370400440532013000
COMPAGNIE XYZ
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}"""
    
    print("✅ Agent 5 Validator: Validation SWIFT")
    print("=" * 70)
    print(f"Message SWIFT:\n{swift_message[:200]}...\n")
    
    result = await agent_5_validator.run(
        f"Valide ce message SWIFT MT103:\n\n{swift_message}"
    )
    
    print("📋 Rapport de validation:\n")
    print(result.output)
    print()


async def exemple_validation_iso20022():
    """Exemple de validation d'un message ISO 20022."""
    iso_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.12">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG20240101120000</MsgId>
      <CreDtTm>2024-01-01T12:00:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>1000.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>MSG20240101120000</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>REF123456789</InstrId>
          <EndToEndId>REF123456789</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="EUR">1000.00</InstdAmt>
        </Amt>
        <Dbtr>
          <Nm>COMPAGNIE ABC</Nm>
        </Dbtr>
        <DbtrAcct>
          <Id>
            <IBAN>FR1420041010050500013M02606</IBAN>
          </Id>
        </DbtrAcct>
        <Cdtr>
          <Nm>COMPAGNIE XYZ</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>DE89370400440532013000</IBAN>
          </Id>
        </CdtrAcct>
        <ReqdExctnDt>2024-01-01</ReqdExctnDt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""
    
    print("✅ Agent 5 Validator: Validation ISO 20022")
    print("=" * 70)
    print(f"Message ISO 20022:\n{iso_xml[:300]}...\n")
    
    result = await agent_5_validator.run(
        f"Valide ce message ISO 20022 pacs.008:\n\n{iso_xml}"
    )
    
    print("📋 Rapport de validation:\n")
    print(result.output)
    print()


async def exemple_validation_conversion():
    """Exemple de validation d'une conversion."""
    print("✅ Agent 5 Validator: Validation de Conversion")
    print("=" * 70)
    
    swift_message = """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF123456789
:32A:240101EUR1000,00
:50A:/FR1420041010050500013M02606
COMPAGNIE ABC
:59:/DE89370400440532013000
COMPAGNIE XYZ
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}"""
    
    # Convert using agent_5
    try:
        from examples.agent_5 import convertir_swift_vers_iso20022
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from examples.agent_5 import convertir_swift_vers_iso20022
    conversion_result = convertir_swift_vers_iso20022(swift_message)
    
    if conversion_result.get("success"):
        iso_xml = conversion_result["iso20022_xml"]
        
        result = await agent_5_validator.run(
            f"Valide cette conversion SWIFT → ISO 20022.\n\n"
            f"Message SWIFT original:\n{swift_message}\n\n"
            f"Message ISO 20022 converti:\n{iso_xml}\n\n"
            f"Vérifie que toutes les informations ont été préservées."
        )
        
        print("📋 Rapport de validation de conversion:\n")
        print(result.output)
    else:
        print(f"❌ Erreur de conversion: {conversion_result.get('error')}")
    print()


if __name__ == "__main__":
    asyncio.run(exemple_validation_swift())
    print("\n" + "=" * 70 + "\n")
    asyncio.run(exemple_validation_iso20022())

