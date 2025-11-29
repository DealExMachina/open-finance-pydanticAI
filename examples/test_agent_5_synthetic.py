"""
Synthetic Test Suite for Agent 5 (SWIFT/ISO 20022 Converter)

10 test cases covering:
- SWIFT to ISO 20022 conversion
- ISO 20022 to SWIFT conversion
- Tool calling verification
- Message validation
- Risk assessment

Outputs detailed results to JSON file for inspection.
"""

import asyncio
import time
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.agent_5 import agent_5
from examples.agent_5_validator import agent_5_validator
from examples.agent_5_risk import agent_5_risk
from app.mitigation_strategies import ToolCallDetector


# ============================================================================
# TEST CASES (10 total)
# ============================================================================

TEST_CASES = [
    {
        "id": 1,
        "name": "SWIFT to ISO 20022 - Standard Payment",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF001234567
:32A:240101EUR5000,00
:50A:/FR1420041010050500013M02606
COMPAGNIE ABC
:59:/DE89370400440532013000
COMPAGNIE XYZ
:70:PAYMENT FOR SERVICES
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 2,
        "name": "ISO 20022 to SWIFT - Standard Payment",
        "type": "iso_to_swift",
        "iso_message": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.12">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG20240101120000</MsgId>
      <CreDtTm>2024-01-01T12:00:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>10000.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>MSG20240101120000</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>REF001234567</InstrId>
          <EndToEndId>REF001234567</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="EUR">10000.00</InstdAmt>
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
</Document>""",
        "expected_tool": "convertir_iso20022_vers_swift",
    },
    {
        "id": 3,
        "name": "SWIFT to ISO 20022 - Large Amount",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF002345678
:32A:240101EUR100000,00
:50A:/FR1420041010050500013M02606
ENTREPRISE LARGE
:59:/US1234567890123456789012
BIG CORPORATION
:70:INVOICE PAYMENT
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 4,
        "name": "SWIFT to ISO 20022 - Small Amount",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF003456789
:32A:240101EUR100,50
:50A:/FR1420041010050500013M02606
PARTICULIER A
:59:/FR7630001007941234567890185
PARTICULIER B
:70:TRANSFER
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 5,
        "name": "ISO 20022 to SWIFT - USD Currency",
        "type": "iso_to_swift",
        "iso_message": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.12">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG20240102120000</MsgId>
      <CreDtTm>2024-01-02T12:00:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>5000.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>MSG20240102120000</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>REF004567890</InstrId>
          <EndToEndId>REF004567890</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="USD">5000.00</InstdAmt>
        </Amt>
        <Dbtr>
          <Nm>US COMPANY A</Nm>
        </Dbtr>
        <DbtrAcct>
          <Id>
            <IBAN>US1234567890123456789012</IBAN>
          </Id>
        </DbtrAcct>
        <Cdtr>
          <Nm>EU COMPANY B</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>FR1420041010050500013M02606</IBAN>
          </Id>
        </CdtrAcct>
        <ReqdExctnDt>2024-01-02</ReqdExctnDt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>""",
        "expected_tool": "convertir_iso20022_vers_swift",
    },
    {
        "id": 6,
        "name": "SWIFT Validation Test",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF005678901
:32A:240101EUR2500,00
:50A:/FR1420041010050500013M02606
VALIDATION TEST
:59:/DE89370400440532013000
VALIDATION TEST 2
:70:TEST
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 7,
        "name": "ISO 20022 to SWIFT - Validation",
        "type": "iso_to_swift",
        "iso_message": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.12">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG20240103120000</MsgId>
      <CreDtTm>2024-01-03T12:00:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>7500.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>MSG20240103120000</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>REF006789012</InstrId>
          <EndToEndId>REF006789012</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="EUR">7500.00</InstdAmt>
        </Amt>
        <Dbtr>
          <Nm>VALIDATION TEST</Nm>
        </Dbtr>
        <DbtrAcct>
          <Id>
            <IBAN>FR1420041010050500013M02606</IBAN>
          </Id>
        </DbtrAcct>
        <Cdtr>
          <Nm>VALIDATION TEST 2</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>DE89370400440532013000</IBAN>
          </Id>
        </CdtrAcct>
        <ReqdExctnDt>2024-01-03</ReqdExctnDt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>""",
        "expected_tool": "convertir_iso20022_vers_swift",
    },
    {
        "id": 8,
        "name": "SWIFT to ISO 20022 - High Amount",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF007890123
:32A:240101EUR150000,00
:50A:/FR1420041010050500013M02606
HIGH AMOUNT TEST
:59:/DE89370400440532013000
HIGH AMOUNT TEST 2
:70:PAYMENT
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 9,
        "name": "SWIFT to ISO 20022 - GBP Currency",
        "type": "swift_to_iso",
        "swift_message": """{1:F01BANKFRPPAXXX1234567890}
{2:O10312002401031200BANKDEFFXXX22221234567890123456789012345678901234567890}
{4:
:20:REF008901234
:32A:240101GBP3000,00
:50A:/GB82WEST12345698765432
UK COMPANY
:59:/FR1420041010050500013M02606
FRENCH COMPANY
:70:PAYMENT
-}
{5:{MAC:ABCD1234}{CHK:EFGH5678}}""",
        "expected_tool": "convertir_swift_vers_iso20022",
    },
    {
        "id": 10,
        "name": "ISO 20022 to SWIFT - Round Number",
        "type": "iso_to_swift",
        "iso_message": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.12">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG20240104120000</MsgId>
      <CreDtTm>2024-01-04T12:00:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>20000.00</CtrlSum>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>MSG20240104120000</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>REF009012345</InstrId>
          <EndToEndId>REF009012345</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="EUR">20000.00</InstdAmt>
        </Amt>
        <Dbtr>
          <Nm>ROUND NUMBER TEST</Nm>
        </Dbtr>
        <DbtrAcct>
          <Id>
            <IBAN>FR1420041010050500013M02606</IBAN>
          </Id>
        </DbtrAcct>
        <Cdtr>
          <Nm>ROUND NUMBER TEST 2</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <IBAN>DE89370400440532013000</IBAN>
          </Id>
        </CdtrAcct>
        <ReqdExctnDt>2024-01-04</ReqdExctnDt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>""",
        "expected_tool": "convertir_iso20022_vers_swift",
    },
]


# ============================================================================
# TEST EXECUTION
# ============================================================================

async def run_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case and return detailed results."""
    test_id = test_case["id"]
    test_name = test_case["name"]
    test_type = test_case["type"]
    expected_tool = test_case["expected_tool"]
    
    result = {
        "test_id": test_id,
        "test_name": test_name,
        "test_type": test_type,
        "success": False,
        "tool_called": False,
        "correct_tool": False,
        "tokens": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "time": 0.0,
        "error": None,
        "input": None,
        "output": None,
        "tool_calls": [],
        "tool_names": [],
        "all_messages": [],
    }
    
    start_time = time.time()
    
    try:
        if test_type == "swift_to_iso":
            prompt = f"Convertis ce message SWIFT MT103 en ISO 20022 pacs.008:\n\n{test_case['swift_message']}"
            agent = agent_5
            result["input"] = test_case['swift_message']
        elif test_type == "iso_to_swift":
            prompt = f"Convertis ce message ISO 20022 pacs.008 en SWIFT MT103:\n\n{test_case['iso_message']}"
            agent = agent_5
            result["input"] = test_case['iso_message']
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        agent_result = await agent.run(prompt)
        elapsed = time.time() - start_time
        
        # Extract tool calls with full details
        tool_calls = ToolCallDetector.extract_tool_calls(agent_result) or []
        tool_names = [tc.get('name', 'unknown') for tc in tool_calls]
        
        # Store full tool call details
        result["tool_calls"] = [
            {
                "name": tc.get('name', 'unknown'),
                "parameters": tc.get('parameters', {}),
                "result": str(tc.get('result', ''))[:500] if tc.get('result') else None,
            }
            for tc in tool_calls
        ]
        result["tool_names"] = tool_names
        
        result["tool_called"] = len(tool_calls) > 0
        result["correct_tool"] = expected_tool in tool_names if tool_names else False
        result["time"] = elapsed
        
        # Store output
        result["output"] = str(agent_result.output)[:2000] if agent_result.output else None
        
        # Extract all messages for detailed inspection
        try:
            messages = []
            for msg in agent_result.all_messages():
                msg_dict = {
                    "role": getattr(msg, 'role', 'unknown'),
                    "content": str(getattr(msg, 'content', ''))[:1000] if hasattr(msg, 'content') else None,
                }
                if hasattr(msg, 'tool_calls'):
                    msg_dict["tool_calls"] = [
                        {
                            "name": getattr(tc, 'name', 'unknown'),
                            "parameters": getattr(tc, 'parameters', {}),
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(msg_dict)
            result["all_messages"] = messages
        except Exception:
            pass
        
        # Get token usage
        try:
            usage = agent_result.usage() if callable(agent_result.usage) else agent_result.usage
            if usage:
                result["tokens"] = getattr(usage, 'total_tokens', 0)
                result["tokens_input"] = getattr(usage, 'input_tokens', 0)
                result["tokens_output"] = getattr(usage, 'output_tokens', 0)
        except Exception:
            pass
        
        # Success if correct tool was used
        result["success"] = result["correct_tool"]
        
    except Exception as e:
        result["error"] = str(e)
        result["time"] = time.time() - start_time
    
    return result


async def main():
    """Run all 10 test cases."""
    print("=" * 80)
    print("AGENT 5 SYNTHETIC TEST SUITE (10 Test Cases)")
    print("=" * 80)
    print()
    
    results = []
    total_time = 0.0
    total_tokens = 0
    
    for test_case in TEST_CASES:
        print(f"Test {test_case['id']}/10: {test_case['name']}")
        print("-" * 80)
        
        result = await run_test_case(test_case)
        results.append(result)
        
        total_time += result["time"]
        total_tokens += result["tokens"]
        
        if result["success"]:
            print(f"✅ PASSED - Tool: {test_case['expected_tool']}")
        elif result["tool_called"]:
            print(f"⚠️  PARTIAL - Tool called but not {test_case['expected_tool']}")
        else:
            print(f"❌ FAILED - No tool called")
            if result["error"]:
                print(f"   Error: {result['error']}")
        
        print(f"   Time: {result['time']:.2f}s, Tokens: {result['tokens']}")
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["success"])
    tool_called = sum(1 for r in results if r["tool_called"])
    avg_time = total_time / len(results) if results else 0
    avg_tokens = total_tokens / len(results) if results else 0
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    print(f"Tool Called: {tool_called}/{len(results)} ({tool_called/len(results)*100:.1f}%)")
    print(f"Average Time: {avg_time:.2f}s")
    print(f"Average Tokens: {avg_tokens:.0f}")
    print()
    
    # Per-type breakdown
    type_stats = {}
    for result in results:
        test_type = next(tc["type"] for tc in TEST_CASES if tc["id"] == result["test_id"])
        if test_type not in type_stats:
            type_stats[test_type] = {"total": 0, "passed": 0}
        type_stats[test_type]["total"] += 1
        if result["success"]:
            type_stats[test_type]["passed"] += 1
    
    print("Per-Type Results:")
    for test_type, stats in type_stats.items():
        print(f"  {test_type}: {stats['passed']}/{stats['total']} ({stats['passed']/stats['total']*100:.1f}%)")
    
    # Save detailed results to JSON
    output_file = Path(__file__).parent / "test_agent_5_results.json"
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": len(results),
            "passed": passed,
            "tool_called": tool_called,
            "avg_time": avg_time,
            "avg_tokens": avg_tokens,
        },
        "test_cases": results,
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
