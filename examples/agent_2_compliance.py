"""
Agent 2 Compliance: Wrapper that executes agent_2 (financial calculator) and runs compliance checks.

Optimizations:
- Uses optimized agent_2 with structured tool returns
- Optimized tool signatures (normalized inputs)
- Concise compliance agent prompt
- Better tool call detection
"""

import asyncio
from typing import List, Tuple
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic_ai import Agent, ModelSettings
from app.models import finance_model
from app.mitigation_strategies import ToolCallDetector

# Import optimized agent_2
from examples.agent_2 import agent_2


async def run_finance_agent(question: str):
    """Execute the financial agent and return (result, tool_calls_log)."""
    result = await agent_2.run(question)
    
    # Use ToolCallDetector for better extraction
    tool_calls = ToolCallDetector.extract_tool_calls(result) or []
    
    # Format tool calls for compliance check
    tool_calls_log: List[str] = []
    for tc in tool_calls:
        name = tc.get('name', 'unknown')
        args = tc.get('args', {})
        args_str = ', '.join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
        tool_calls_log.append(f"{name}({args_str})")
    
    return result, tool_calls_log


# ============================================================================
# OPTIMIZED COMPLIANCE AGENT
# ============================================================================

compliance_agent = Agent(
    finance_model,
    model_settings=ModelSettings(max_output_tokens=400),  # Reduced from 600
    system_prompt="""Contrôleur compliance pour calculs financiers.
Règles:
1. Liste d'outils vide → Non conforme
2. Outils utilisés → Conforme, mentionner lesquels
3. Calcul mentionné sans outil → Flag potential issue
Réponse: 'Conforme' ou 'Non conforme' + justification courte.""",  # 78 tokens vs 120 tokens (35% reduction)
)


async def run_with_compliance(question: str) -> Tuple[str, List[str], str]:
    """Run financial agent with compliance check.
    
    Returns:
        (agent_response, tool_calls, compliance_verdict)
    """
    result, tool_calls = await run_finance_agent(question)
    
    compliance_input = (
        f"QUESTION CLIENT:\n{question}\n\n"
        f"RÉPONSE FOURNIE:\n{result.output}\n\n"
        f"APPELS D'OUTILS:\n{chr(10).join(tool_calls) if tool_calls else 'Aucun'}"
    )
    
    compliance_result = await compliance_agent.run(compliance_input)
    compliance_verdict = str(compliance_result.output)
    
    return str(result.output), tool_calls, compliance_verdict


async def exemple_compliance_check():
    """Example of compliance checking."""
    print("📊 Agent 2 Compliance: Financial Calculations with Compliance Check")
    print("=" * 70)
    
    questions = [
        "J'ai 25 000€ à 4% pendant 8 ans. Combien aurai-je?",
        "J'emprunte 150 000€ sur 15 ans à 2.8%. Quel est le versement mensuel?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*70}")
        print(f"Question {i}: {question}")
        print("="*70)
        
        try:
            import time
            start = time.time()
            response, tool_calls, compliance = await run_with_compliance(question)
            elapsed = time.time() - start
            
            print(f"\n✅ Réponse Agent:")
            print(f"{response}\n")
            
            print(f"🔧 Appels d'outils détectés:")
            if tool_calls:
                for tc in tool_calls:
                    print(f"  - {tc}")
            else:
                print("  ⚠️ Aucun (non conforme)")
            
            print(f"\n🔍 Avis Compliance:")
            print(f"{compliance}")
            
            print(f"\n⏱️  Temps: {elapsed:.2f}s")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 70 + "\n")


async def main():
    """Main function."""
    await exemple_compliance_check()


if __name__ == "__main__":
    asyncio.run(main())
