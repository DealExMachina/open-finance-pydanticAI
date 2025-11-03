"""
Jeu de tests pour vérifier le parsing de messages SWIFT.

Teste différents formats et cas limites pour s'assurer que l'extraction
fonctionne correctement avec validation Pydantic.
"""

import sys
from pathlib import Path

# Ajouter le répertoire au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from swift_extractor import (
    parse_swift_mt103_advanced,
    SwiftMT103Parsed,
    extract_iban_from_text,
    extract_bic_from_text,
    parse_swift_field_32a,
)


# ============================================================================
# MESSAGES SWIFT DE TEST
# ============================================================================

TEST_MESSAGE_1_SIMPLE = """
:20:NONREF
:23B:CRED
:32A:241215EUR15000.00
:50K:/FR76300040000100000000000123
ORDRE DUPONT JEAN
:59:/FR1420041010050500013M02606
BENEFICIAIRE MARTIN PIERRE
:70:Paiement facture décembre 2024
:71A:OUR
"""

TEST_MESSAGE_2_FULL_DATE = """
:20:INVOICE-2024-001
:23B:CRED
:32A:20241215EUR25000.50
:50K:/FR76300040000100000000000123
ORDRE DUPONT JEAN
RUE DE LA REPUBLIQUE 123
75001 PARIS FRANCE
:52A:BNPAFRPPXXX
:56A:SOGEFRPPXXX
:57A:CRLYFRPPXXX
:59:/FR1420041010050500013M02606
BENEFICIAIRE MARTIN PIERRE
AVENUE DES CHAMPS ELYSEES 456
75008 PARIS FRANCE
:70:Paiement facture décembre 2024
Référence: INV-001
:71A:SHA
:72:/INS/BANQUE INTERMEDIAIRE
"""

TEST_MESSAGE_3_MULTILINE = """
:20:TXN-2025-001
:23B:CRED
:32A:250120USD50000.00
:50K:/US64SVBKUS6SXXX123456789
COMPANY ABC INC
123 MAIN STREET
NEW YORK NY 10001
UNITED STATES
:52A:ABCDUS33XXX
:59:/GB82WEST12345698765432
BENEFICIARY XYZ LTD
456 HIGH STREET
LONDON EC1A 1BB
UNITED KINGDOM
:70:Payment for services Q1 2025
Contract reference: CONTRACT-2025-001
Invoice: INV-2025-042
:71A:BEN
:72:/INS/Urgent payment requested
"""

TEST_MESSAGE_4_EUROPEAN = """
:20:PAY-2024-042
:23B:CRED
:32A:241231CHF125000.00
:50K:/CH9300762011623852957
SWISS COMPANY AG
BAHNHOFSTRASSE 1
8001 ZURICH
SWITZERLAND
:52A:UBSWCHZH80A
:57A:DEUTDEFFXXX
:59:/DE89370400440532013000
GERMAN BENEFICIARY GMBH
FRIEDRICHSTRASSE 100
10117 BERLIN
GERMANY
:70:Year-end payment 2024
:71A:OUR
:72:/INS/Final payment of the year
"""

TEST_MESSAGE_5_MINIMAL = """
:20:MIN-REF-001
:23B:CRED
:32A:250101EUR100.00
:50K:/FR76300040000100000000000123
CUSTOMER NAME
:59:/FR1420041010050500013M02606
BENEFICIARY NAME
:71A:OUR
"""

TEST_MESSAGE_6_WITH_COMMA_ENGLISH = """
:20:REF-COMMA-ENG
:23B:CRED
:32A:250101EUR1,234.56
:50K:/FR76300040000100000000000123
ORDERING CUSTOMER
:59:/FR1420041010050500013M02606
BENEFICIARY CUSTOMER
:70:Test with comma as thousands separator (English format)
:71A:OUR
"""

TEST_MESSAGE_6_WITH_COMMA_EUROPEAN = """
:20:REF-COMMA-EUR
:23B:CRED
:32A:250101EUR1.234,56
:50K:/FR76300040000100000000000123
ORDERING CUSTOMER
:59:/FR1420041010050500013M02606
BENEFICIARY CUSTOMER
:70:Test with dot for thousands and comma for decimals (European format)
:71A:OUR
"""

TEST_MESSAGE_7_INTERNATIONAL = """
:20:INTL-TXN-001
:23B:CRED
:32A:250215JPY1000000.00
:50K:/JP9123456789012345678901
JAPANESE COMPANY CO LTD
TOKYO 100-0001
JAPAN
:52A:MHCBJPJTXXX
:56A:CHASUS33XXX
:57A:HSBCGB2LXXX
:59:/GB29NWBK60161331926819
UK BENEFICIARY LTD
LONDON
:70:International transfer
:71A:SHA
:72:/INS/Correspondent bank details
"""


# ============================================================================
# TESTS
# ============================================================================

def test_field_32a_parsing():
    """Test le parsing du champ :32A: avec différents formats."""
    print("\n" + "=" * 60)
    print("TEST: Parsing champ :32A:")
    print("=" * 60)
    
    test_cases = [
        ("241215EUR15000.00", "2024-12-15", "EUR", 15000.0),  # YYMMDD
        ("20241215EUR15000.00", "2024-12-15", "EUR", 15000.0),  # YYYYMMDD
        ("250101USD100.50", "2025-01-01", "USD", 100.5),  # Format court
        ("991231GBP5000.00", "1999-12-31", "GBP", 5000.0),  # Année 99 → 1999
    ]
    
    for value, expected_date, expected_currency, expected_amount in test_cases:
        try:
            parsed = parse_swift_field_32a(value)
            assert parsed.value_date == expected_date.replace("-", ""), \
                f"Date mismatch: {parsed.value_date} != {expected_date}"
            assert parsed.currency == expected_currency, \
                f"Currency mismatch: {parsed.currency} != {expected_currency}"
            assert parsed.amount == expected_amount, \
                f"Amount mismatch: {parsed.amount} != {expected_amount}"
            print(f"✅ {value} → {parsed.value_date} {parsed.currency} {parsed.amount}")
        except Exception as e:
            print(f"❌ {value} → ERREUR: {e}")


def test_iban_extraction():
    """Test l'extraction d'IBAN depuis du texte."""
    print("\n" + "=" * 60)
    print("TEST: Extraction IBAN")
    print("=" * 60)
    
    test_cases = [
        ("/FR76 3000 4000 0100 0000 0000 123", "FR76300040000100000000000123"),
        ("FR1420041010050500013M02606", "FR1420041010050500013M02606"),
        ("Compte: GB82WEST12345698765432", "GB82WEST12345698765432"),
        ("IBAN: CH9300762011623852957 dans le texte", "CH9300762011623852957"),
    ]
    
    for text, expected in test_cases:
        iban = extract_iban_from_text(text)
        if iban == expected:
            print(f"✅ '{text[:40]}...' → {iban}")
        else:
            print(f"❌ '{text[:40]}...' → {iban} (attendu: {expected})")


def test_bic_extraction():
    """Test l'extraction de BIC depuis du texte."""
    print("\n" + "=" * 60)
    print("TEST: Extraction BIC")
    print("=" * 60)
    
    test_cases = [
        ("BNPAFRPPXXX", "BNPAFRPPXXX"),
        ("BIC: SOGEFRPPXXX", "SOGEFRPPXXX"),
        ("Bank: ABCDUS33", "ABCDUS33"),
        ("BIC ABCDUS33XXX in text", "ABCDUS33XXX"),
    ]
    
    for text, expected in test_cases:
        bic = extract_bic_from_text(text)
        if bic == expected:
            print(f"✅ '{text}' → {bic}")
        else:
            print(f"❌ '{text}' → {bic} (attendu: {expected})")


def test_swift_parsing(message_name: str, message: str, description: str = ""):
    """Test le parsing d'un message SWIFT complet."""
    print(f"\n{'=' * 60}")
    print(f"TEST: {message_name}")
    if description:
        print(f"Description: {description}")
    print("=" * 60)
    
    try:
        parsed = parse_swift_mt103_advanced(message)
        
        print(f"✅ Parsing réussi!")
        print(f"  Référence: {parsed.field_20}")
        print(f"  Date: {parsed.field_32A.value_date}")
        print(f"  Devise: {parsed.field_32A.currency}")
        print(f"  Montant: {parsed.field_32A.amount:,.2f} {parsed.field_32A.currency}")
        
        if parsed.ordering_customer_account:
            print(f"  IBAN ordonnateur: {parsed.ordering_customer_account}")
        if parsed.beneficiary_account:
            print(f"  IBAN bénéficiaire: {parsed.beneficiary_account}")
        if parsed.field_52A:
            print(f"  BIC banque ordonnateur: {parsed.field_52A}")
        if parsed.field_56A:
            print(f"  BIC banque intermédiaire: {parsed.field_56A}")
        if parsed.field_57A:
            print(f"  BIC banque bénéficiaire: {parsed.field_57A}")
        if parsed.field_70:
            print(f"  Motif: {parsed.field_70[:50]}...")
        print(f"  Frais: {parsed.field_71A}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "=" * 60)
    print("SUITE DE TESTS - PARSING SWIFT")
    print("=" * 60)
    
    results = []
    
    # Tests unitaires
    test_field_32a_parsing()
    test_iban_extraction()
    test_bic_extraction()
    
    # Tests de parsing complets
    results.append(("Message simple", test_swift_parsing(
        "Message simple (YYMMDD)",
        TEST_MESSAGE_1_SIMPLE,
        "Format basique avec date YYMMDD"
    )))
    
    results.append(("Message complet", test_swift_parsing(
        "Message complet (YYYYMMDD)",
        TEST_MESSAGE_2_FULL_DATE,
        "Tous les champs avec banques intermédiaires"
    )))
    
    results.append(("Multi-lignes", test_swift_parsing(
        "Message multi-lignes",
        TEST_MESSAGE_3_MULTILINE,
        "Adresses complètes sur plusieurs lignes"
    )))
    
    results.append(("Européen", test_swift_parsing(
        "Message européen",
        TEST_MESSAGE_4_EUROPEAN,
        "IBAN suisse et allemand"
    )))
    
    results.append(("Minimal", test_swift_parsing(
        "Message minimal",
        TEST_MESSAGE_5_MINIMAL,
        "Uniquement les champs obligatoires"
    )))
    
    results.append(("Format anglais", test_swift_parsing(
        "Message avec virgule (format anglais)",
        TEST_MESSAGE_6_WITH_COMMA_ENGLISH,
        "Montant 1,234.56 (virgule = milliers, point = décimales)"
    )))
    
    results.append(("Format européen", test_swift_parsing(
        "Message avec virgule (format européen)",
        TEST_MESSAGE_6_WITH_COMMA_EUROPEAN,
        "Montant 1.234,56 (point = milliers, virgule = décimales)"
    )))
    
    results.append(("International", test_swift_parsing(
        "Message international",
        TEST_MESSAGE_7_INTERNATIONAL,
        "Transfert intercontinental avec JPY"
    )))
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés!")
    else:
        print(f"\n⚠️ {total - passed} test(s) ont échoué")


if __name__ == "__main__":
    run_all_tests()

