"""
Gradio GUI for Open Finance PydanticAI Agents.

Clean tabbed interface with server health checks and tool usage tracking.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import gradio as gr
import httpx

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config import Settings, ENDPOINTS


# ============================================================================
# GLOBAL STATE
# ============================================================================

results_store: Dict[str, Any] = {}

# Agent descriptions
AGENT_INFO = {
    "Agent 1": {
        "title": "Portfolio Extractor",
        "description": "Extracts structured portfolio data from natural language text. Identifies stock symbols, quantities, prices, and calculates total values.",
        "default_input": "Extrais le portfolio: 50 AIR.PA a 120 euros, 30 SAN.PA a 85 euros, 100 TTE.PA a 55 euros",
    },
    "Agent 2": {
        "title": "Financial Calculator", 
        "description": "Performs precise financial calculations using numpy-financial. Computes future values, loan payments, portfolio performance, and interest rates. Ask ONE question at a time.",
        "default_input": "J'ai 50000 euros a placer a 4% par an pendant 10 ans. Quelle sera la valeur finale?",
    },
    "Agent 3": {
        "title": "Risk and Tax Advisor",
        "description": "Multi-agent workflow combining risk analysis and tax optimization. Evaluates portfolio risk levels and provides tax-efficient recommendations.",
        "default_input": "Analyse le risque d'un portfolio: 40% actions, 30% obligations, 20% immobilier, 10% autres. Investissement 100k euros, horizon 30 ans.",
    },
    "Agent 4": {
        "title": "Option Pricing",
        "description": "Prices European options using QuantLib Black-Scholes model. Computes option prices and Greeks (delta, gamma, theta, vega, rho).",
        "default_input": "Prix d'un call europeen: Spot=100, Strike=105, Maturite=0.5 an, Taux=0.02, Volatilite=0.25, Dividende=0.01",
    },
    "Agent 5 - Convert": {
        "title": "Message Conversion",
        "description": "Bidirectional: SWIFT MT103 ↔ ISO 20022 pacs.008. Use convertir_swift_vers_iso20022 or convertir_iso20022_vers_swift",
        "default_input": """Convertis ce SWIFT MT103 vers ISO 20022:

{1:F01BANKFRPPAXXX1234567890}
{4:
:20:REF123
:32A:240101EUR1000,00
:50A:/FR1420041010050500013M02606
COMPAGNIE ABC
:59:/DE89370400440532013000
COMPAGNIE XYZ
-}

Pour la direction inverse (ISO→SWIFT), fournis un XML ISO 20022 et demande la conversion vers SWIFT.""",
    },
    "Agent 5 - Validate": {
        "title": "Message Validation",
        "description": "Validates SWIFT MT and ISO 20022 message structure, format, and required fields",
        "default_input": """{1:F01BANKFRPPAXXX1234567890}
{4:
:20:REF123
:32A:240101EUR1000,00
-}""",
    },
    "Agent 5 - Risk": {
        "title": "Risk Assessment",
        "description": "AML/KYC risk scoring for financial messages. Evaluates transaction patterns and risk indicators.",
        "default_input": """{1:F01BANKUSAAXXX1234567890}
{4:
:20:REF999
:32A:240101USD50000,00
:50A:/US1234567890
SENDER COMPANY INC
:59:/RU9876543210
RUSSIAN ENTITY LLC
-}""",
    },
    "Agent 6": {
        "title": "Judge Agent",
        "description": "Critical evaluator using a larger model (70B). Reviews outputs from other agents for correctness, completeness, and quality.",
        "default_input": "Evaluate the quality and accuracy of all previous agent results.",
    },
}


# ============================================================================
# HEALTH CHECKS
# ============================================================================

def check_server_health(endpoint_name: str, base_url: str, timeout: float = 3.0, api_key: Optional[str] = None) -> Tuple[bool, str]:
    """Check if a server endpoint is accessible. Returns (is_online, status).
    
    Status values:
    - "online": Server is up and responding
    - "sleeping": Server is sleeping (Koyeb specific)
    - "offline": Server is down or unreachable
    """
    if not base_url:
        return False, "offline"
    
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            # LLM Pro Finance uses /api (not /api/v1)
            if endpoint_name == "llm_pro":
                url = f"{base_url}/api/models"
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                try:
                    r = client.get(url, headers=headers)
                    # 200 = OK, 401 = auth required (server is up), 403 = forbidden (server is up)
                    if r.status_code in [200, 401, 403]:
                        return True, "online"
                    # Check if valid JSON response (API exists)
                    try:
                        json.loads(r.text)
                        return True, "online"
                    except:
                        pass
                except:
                    pass
                # Fallback to root
                try:
                    r = client.get(base_url, timeout=timeout)
                    if r.status_code in [200, 401, 403]:
                        return True, "online"
                except:
                    pass
                return False, "offline"
            
            # Koyeb/HF
            urls = [f"{base_url}/v1/models", f"{base_url}/health", base_url]
            sleeping_detected = False
            timeout_detected = False
            
            for url in urls:
                try:
                    r = client.get(url)
                    if r.status_code in [200, 401]:
                        return True, "online"
                    # 404 might mean sleeping service or endpoint doesn't exist
                    if r.status_code == 404:
                        # If it's the "no active service" page, service is sleeping (Koyeb specific)
                        if "no active service" in r.text.lower() and endpoint_name == "koyeb":
                            sleeping_detected = True
                            continue  # Check other URLs first
                        # Regular 404 - endpoint doesn't exist but server might be up
                        # Accept it if it's not the sleeping page
                        return True, "online"
                    # 503 might mean service is paused (HF Spaces)
                    if r.status_code == 503:
                        if endpoint_name == "hf":
                            return False, "offline"  # HF is paused
                except httpx.TimeoutException:
                    # Timeout might mean service is sleeping (especially for Koyeb)
                    if endpoint_name == "koyeb":
                        timeout_detected = True
                    continue
                except Exception as e:
                    # Other errors - continue to next URL
                    continue
            
            # For Koyeb, timeout or sleeping page means sleeping
            if endpoint_name == "koyeb" and (sleeping_detected or timeout_detected):
                return False, "sleeping"
            
            # If we detected sleeping state, return that
            if sleeping_detected:
                return False, "sleeping"
            
            return False, "offline"
    except:
        return False, "offline"


def wake_up_koyeb_service(base_url: str) -> Tuple[bool, str]:
    """Attempt to wake up a sleeping Koyeb service."""
    if not base_url:
        return False, "No URL configured"
    
    try:
        # Make a request with longer timeout to wake up the service
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            # Try multiple endpoints to wake it up
            wake_urls = [
                f"{base_url}/v1/models",
                f"{base_url}/v1/chat/completions",
                base_url,
            ]
            
            last_error = None
            for url in wake_urls:
                try:
                    print(f"[WAKE] Attempting to wake Koyeb: {url}")
                    r = client.get(url, timeout=30.0)
                    print(f"[WAKE] Response: {r.status_code} from {url}")
                    
                    # If we get a response (even 404), the service is waking up
                    if r.status_code in [200, 401, 404]:
                        # Check if it's still sleeping
                        if r.status_code == 404 and "no active service" in r.text.lower():
                            print(f"[WAKE] Still sleeping, trying next URL...")
                            last_error = "Service still sleeping (404 with 'no active service')"
                            continue  # Still sleeping, try next URL
                        # Success - service is responding
                        print(f"[WAKE] Service responding with status {r.status_code}")
                        return True, f"Service waking up (status {r.status_code})"
                    elif r.status_code == 503:
                        # Service unavailable but responding - might be waking
                        print(f"[WAKE] Service unavailable (503) - may be waking up")
                        return True, "Service waking up (503 - unavailable but responding)"
                except httpx.TimeoutException:
                    print(f"[WAKE] Timeout on {url} - service may be cold starting")
                    last_error = "Timeout - service may be cold starting"
                    continue
                except httpx.ConnectError as e:
                    print(f"[WAKE] Connection error on {url}: {e}")
                    last_error = f"Connection error: {str(e)[:50]}"
                    continue
                except Exception as e:
                    print(f"[WAKE] Error on {url}: {e}")
                    last_error = f"Error: {str(e)[:50]}"
                    continue
            
            return False, last_error or "Service still sleeping after all attempts"
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"[WAKE] Fatal error: {error_msg}")
        return False, f"Error: {error_msg}"


def get_status_html() -> str:
    """Get status indicators HTML with wake-up buttons."""
    settings = Settings()
    
    servers = [
        ("koyeb", "Koyeb", ENDPOINTS.get("koyeb", {}).get("url", ""), None),
        ("hf", "HuggingFace", ENDPOINTS.get("hf", {}).get("url", ""), None),
        ("llm_pro", "LLM Pro", settings.llm_pro_finance_url or "", settings.llm_pro_finance_key),
    ]
    
    html = "<div style='display: flex; gap: 20px; align-items: center; flex-wrap: wrap; font-family: system-ui;'>"
    for key, name, url, api_key in servers:
        if url:
            is_online, status = check_server_health(key, url, api_key=api_key, timeout=3.0)
        else:
            is_online, status = False, "offline"
        
        # Color coding: green (online), blue (sleeping), red (offline)
        if status == "online":
            color = "#22c55e"
            status_text = "Online"
        elif status == "sleeping":
            color = "#3b82f6"  # Blue
            status_text = "Sleeping"
        else:
            color = "#ef4444"
            status_text = "Offline"
        
        html += f"""
        <div style='display: flex; align-items: center; gap: 6px;'>
            <span style='color: {color}; font-size: 14px; font-weight: bold;'>●</span>
            <span style='font-size: 12px;'>{name}</span>
            <span style='font-size: 11px; color: #6b7280;'>({status_text})</span>
        </div>
        """
    html += "</div>"
    return html


def wake_up_koyeb() -> Tuple[str, str]:
    """Wake up Koyeb service and return updated status HTML and message."""
    koyeb_url = ENDPOINTS.get("koyeb", {}).get("url", "")
    if not koyeb_url:
        return get_status_html(), "❌ Koyeb URL not configured"
    
    print(f"[WAKE] User triggered wake-up for Koyeb: {koyeb_url}")
    success, message = wake_up_koyeb_service(koyeb_url)
    
    if success:
        # Wait a moment for service to wake up, then check status
        import time
        time.sleep(3)
        # Re-check health to get updated status
        ready, status = check_server_health("koyeb", koyeb_url, timeout=15.0)
        if ready:
            return get_status_html(), f"✅ Wake-up successful! Service is now online. {message}"
        else:
            return get_status_html(), f"⏳ Wake-up initiated: {message}. Service may take 10-30 seconds to fully wake up."
    else:
        return get_status_html(), f"❌ Wake-up failed: {message}. Try again in a few seconds."


def is_backend_ready(agent_name: str) -> Tuple[bool, str]:
    """Check if the backend for an agent is ready with detailed diagnostics."""
    settings = Settings()
    
    # Judge uses LLM Pro
    if "Judge" in agent_name or agent_name == "Agent 6":
        url = settings.llm_pro_finance_url or ENDPOINTS.get("llm_pro_finance", {}).get("url", "")
        if not url:
            return False, "LLM Pro Finance URL not configured. Set LLM_PRO_FINANCE_URL in .env"
        
        # Try with longer timeout for sleeping services
        ready, status = check_server_health("llm_pro", url, timeout=5.0, api_key=None)
        if not ready:
            # Try to wake up the service
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    client.get(f"{url}/api/models")
            except:
                pass
            
            # Check again
            ready, status = check_server_health("llm_pro", url, timeout=5.0, api_key=None)
        
        if ready:
            return True, ""
        else:
            return False, f"LLM Pro Finance server not available at {url}. Check if the service is running."
    
    # Other agents: Prefer Koyeb when available, fallback to HF
    koyeb_url = ENDPOINTS.get("koyeb", {}).get("url", "")
    hf_url = ENDPOINTS.get("hf", {}).get("url", "")
    
    # Always check Koyeb first (preferred)
    if koyeb_url:
        ready, status = check_server_health("koyeb", koyeb_url, timeout=5.0)
        
        if not ready and status == "sleeping":
            # Try to wake up Koyeb if it's sleeping
            wake_success, wake_msg = wake_up_koyeb_service(koyeb_url)
            if wake_success:
                import time
                time.sleep(3)
                ready, status = check_server_health("koyeb", koyeb_url, timeout=10.0)
        
        if ready:
            # Koyeb is available - use it for all agents (except Judge)
            return True, ""
    
    # Koyeb not available, check HF as fallback
    if hf_url:
        ready, status = check_server_health("hf", hf_url, timeout=5.0)
        if ready:
            # HF is available as fallback
            return True, ""
    
    # Neither server is available
    koyeb_status_text = "sleeping (use wake-up button)" if status == "sleeping" else "offline"
    hf_status_text = "offline"
    
    if koyeb_url and hf_url:
        return False, f"Koyeb is {koyeb_status_text} and HuggingFace is {hf_status_text}. No LLM servers available."
    elif koyeb_url:
        return False, f"Koyeb is {koyeb_status_text}. No LLM servers available."
    elif hf_url:
        return False, f"HuggingFace is {hf_status_text}. No LLM servers available."
    else:
        return False, "No LLM server URLs configured."


# ============================================================================
# TOOL USAGE EXTRACTION
# ============================================================================

def extract_tool_usage(result) -> Dict[str, Any]:
    """Extract tool usage information from an agent result."""
    tool_info = {"used": False, "count": 0, "names": []}
    
    if not result or not hasattr(result, 'all_messages'):
        return tool_info
    
    try:
        messages = list(result.all_messages())
        for msg in messages:
            # Check for tool calls in the message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_info["used"] = True
                for tc in msg.tool_calls:
                    tool_info["count"] += 1
                    name = getattr(tc, 'name', None) or getattr(tc, 'function', {}).get('name', 'unknown')
                    if name not in tool_info["names"]:
                        tool_info["names"].append(name)
            # Alternative: check parts
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if hasattr(part, 'tool_name'):
                        tool_info["used"] = True
                        tool_info["count"] += 1
                        if part.tool_name not in tool_info["names"]:
                            tool_info["names"].append(part.tool_name)
    except:
        pass
    
    return tool_info


def format_tool_usage_html(tool_info: Dict[str, Any]) -> str:
    """Format tool usage info as HTML."""
    if not tool_info["used"]:
        return "<span style='color: #6b7280;'>No tools used</span>"
    
    names = ", ".join(tool_info["names"]) if tool_info["names"] else "unknown"
    return f"<span style='color: #059669;'>Tools: {tool_info['count']} call(s) - {names}</span>"


def format_detailed_tool_trace(tool_calls: List[str]) -> str:
    """Format detailed tool calling trace as HTML."""
    if not tool_calls:
        return ""
    
    # Warn if excessive tool calls
    warning_html = ""
    if len(tool_calls) > 3:
        warning_html = f"""
        <div style='padding: 8px; margin-bottom: 8px; background: #fef3c7; border-left: 3px solid #f59e0b; border-radius: 3px;'>
            <strong style='font-size: 11px; color: #92400e;'>⚠️ Warning:</strong>
            <span style='font-size: 11px; color: #78350f;'>Excessive tool calls ({len(tool_calls)}). This may cause context length errors. Expected 1-3 calls.</span>
        </div>
        """
    
    html = f"""
    <div style='margin-top: 10px; padding: 10px; background: #f9fafb; border-radius: 6px; border: 1px solid #e5e7eb;'>
        <strong style='font-size: 12px; color: #374151; margin-bottom: 8px; display: block;'>Detailed Tool Call Trace ({len(tool_calls)} calls):</strong>
        {warning_html}
        <div style='font-family: monospace; font-size: 11px; max-height: 300px; overflow-y: auto;'>
    """
    
    for i, tc in enumerate(tool_calls, 1):
        # Parse tool call string (format: "tool_name(arg1=val1, arg2=val2)")
        if '(' in tc:
            tool_name = tc.split('(')[0]
            args_str = tc.split('(')[1].rstrip(')')
            
            html += f"""
            <div style='padding: 6px; margin: 4px 0; background: white; border-left: 3px solid #3b82f6; border-radius: 3px;'>
                <span style='color: #1f2937; font-weight: 600;'>{i}. {tool_name}</span>
                <div style='color: #6b7280; margin-left: 12px; margin-top: 4px;'>{args_str}</div>
            </div>
            """
        else:
            html += f"""
            <div style='padding: 6px; margin: 4px 0; background: white; border-left: 3px solid #3b82f6; border-radius: 3px;'>
                <span style='color: #1f2937; font-weight: 600;'>{i}. {tc}</span>
            </div>
            """
    
    html += """
        </div>
    </div>
    """
    return html


def check_agent_compliance(agent_name: str, output, tool_info: Dict[str, Any]) -> Dict[str, Any]:
    """Check agent compliance and return review."""
    review = {
        "passed": True,
        "checks": [],
        "warnings": [],
        "score": 100
    }
    
    # Agent 2: Financial Calculator compliance
    if agent_name == "Agent 2":
        # Check 1: Tools should be used
        if not tool_info["used"]:
            review["checks"].append(("Tool Usage", False, "No tools used - agent should use financial tools"))
            review["passed"] = False
            review["score"] -= 30
        else:
            review["checks"].append(("Tool Usage", True, f"Used {tool_info['count']} tool(s)"))
        
        # Check 2: Tool calls should be reasonable (1-3 max)
        if tool_info["count"] > 3:
            review["warnings"].append(f"Excessive tool calls: {tool_info['count']} (expected 1-3)")
            review["score"] -= min(20, (tool_info["count"] - 3) * 5)
        
        # Check 3: Output should have required fields
        if hasattr(output, 'model_dump'):
            data = output.model_dump()
            required = ["calculation_type", "result", "input_parameters"]
            missing = [f for f in required if f not in data or data[f] is None]
            if missing:
                review["checks"].append(("Output Fields", False, f"Missing: {', '.join(missing)}"))
                review["score"] -= 20
            else:
                review["checks"].append(("Output Fields", True, "All required fields present"))
        
        # Check 4: Result should be numeric
        if hasattr(output, 'result') and isinstance(output.result, (int, float)):
            review["checks"].append(("Result Type", True, f"Valid numeric result: {output.result:,.2f}"))
        elif hasattr(output, 'model_dump'):
            data = output.model_dump()
            if 'result' in data and isinstance(data['result'], (int, float)):
                review["checks"].append(("Result Type", True, f"Valid numeric result: {data['result']:,.2f}"))
    
    # Agent 3: Risk & Tax Advisor compliance
    elif agent_name == "Agent 3":
        # Check 1: Risk analyst should use portfolio calculation tool
        expected_tool = "calculer_rendement_portfolio"
        if not tool_info["used"]:
            review["checks"].append(("Tool Usage", False, "No tools used - risk analyst should calculate portfolio returns"))
            review["passed"] = False
            review["score"] -= 40
        elif expected_tool not in tool_info["names"]:
            review["checks"].append(("Portfolio Tool", False, f"Expected {expected_tool} to be called"))
            review["score"] -= 30
        else:
            review["checks"].append(("Portfolio Tool", True, "Portfolio return calculation used"))
        
        # Check 2: Output should have both risk and tax analysis
        if isinstance(output, dict):
            has_risk = "risk_analysis" in output and output.get("risk_analysis")
            has_tax = "tax_analysis" in output and output.get("tax_analysis")
            
            if has_risk and has_tax:
                review["checks"].append(("Output Structure", True, "Both risk and tax analyses present"))
            else:
                missing = []
                if not has_risk:
                    missing.append("risk_analysis")
                if not has_tax:
                    missing.append("tax_analysis")
                review["checks"].append(("Output Structure", False, f"Missing: {', '.join(missing)}"))
                review["score"] -= 20
        
        # Check 3: Risk level should be 1-5
        if isinstance(output, dict) and "risk_analysis" in output:
            risk = output["risk_analysis"]
            if isinstance(risk, dict) and "niveau_risque" in risk:
                level = risk["niveau_risque"]
                if 1 <= level <= 5:
                    review["checks"].append(("Risk Level", True, f"Valid risk level: {level}/5"))
                else:
                    review["checks"].append(("Risk Level", False, f"Invalid risk level: {level} (should be 1-5)"))
                    review["score"] -= 15
    
    # Agent 4: Option Pricing compliance
    elif agent_name == "Agent 4":
        # Check 1: Black-Scholes tool should be used
        expected_tool = "calculer_prix_call_black_scholes"
        if not tool_info["used"]:
            review["checks"].append(("QuantLib Tool", False, "Black-Scholes tool not called"))
            review["passed"] = False
            review["score"] -= 40
        elif expected_tool not in tool_info["names"]:
            review["checks"].append(("QuantLib Tool", False, f"Expected {expected_tool}"))
            review["score"] -= 20
        else:
            review["checks"].append(("QuantLib Tool", True, "Black-Scholes pricing used"))
        
        # Check 2: Greeks should be present
        if hasattr(output, 'model_dump'):
            data = output.model_dump()
            greeks = ["delta", "gamma", "vega", "theta"]
            present = [g for g in greeks if g in data and data[g] is not None]
            if len(present) == len(greeks):
                review["checks"].append(("Greeks", True, f"All Greeks calculated: {', '.join(greeks)}"))
            else:
                missing = set(greeks) - set(present)
                review["checks"].append(("Greeks", False, f"Missing Greeks: {', '.join(missing)}"))
                review["score"] -= 15
        
        # Check 3: Option price should be positive
        if hasattr(output, 'option_price'):
            if output.option_price > 0:
                review["checks"].append(("Option Price", True, f"Valid price: {output.option_price:.4f}"))
            else:
                review["checks"].append(("Option Price", False, f"Invalid price: {output.option_price}"))
                review["score"] -= 20
    
    review["score"] = max(0, review["score"])
    return review


def format_compliance_html(review: Dict[str, Any]) -> str:
    """Format compliance review as HTML."""
    if not review["checks"]:
        return ""
    
    score = review["score"]
    score_color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
    
    html = f"""
    <div style='margin-top: 10px; padding: 10px; background: #fafafa; border-radius: 6px; border-left: 3px solid {score_color};'>
        <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
            <strong style='font-size: 12px; color: #374151;'>Compliance Review</strong>
            <span style='font-weight: 600; color: {score_color};'>{score}%</span>
        </div>
    """
    
    for check_name, passed, detail in review["checks"]:
        icon = "✓" if passed else "✗"
        color = "#22c55e" if passed else "#ef4444"
        html += f"""
        <div style='font-size: 11px; margin: 4px 0; display: flex; align-items: center;'>
            <span style='color: {color}; margin-right: 6px;'>{icon}</span>
            <span style='color: #6b7280;'>{check_name}:</span>
            <span style='margin-left: 4px; color: #374151;'>{detail}</span>
        </div>
        """
    
    for warning in review.get("warnings", []):
        html += f"""
        <div style='font-size: 11px; margin: 4px 0; color: #f59e0b;'>
            ⚠ {warning}
        </div>
        """
    
    html += "</div>"
    return html


# ============================================================================
# AGENT EXECUTION
# ============================================================================

async def run_agent_async(agent, prompt: str, output_model=None, agent_name: str = "Agent", timeout_seconds: float = 60.0):
    """Run an agent asynchronously and return results with tool usage."""
    start_time = time.time()
    
    # Check backend
    ready, msg = is_backend_ready(agent_name)
    if not ready:
        return {"error": msg}, None, 0, {}
    
    try:
        # Run with timeout
        if output_model:
            result = await asyncio.wait_for(
                agent.run(prompt, output_type=output_model),
                timeout=timeout_seconds
            )
        else:
            result = await asyncio.wait_for(
                agent.run(prompt),
                timeout=timeout_seconds
            )
        
        elapsed = time.time() - start_time
        output = result.output
        tool_info = extract_tool_usage(result)
        
        # Get usage info
        usage = None
        if hasattr(result, 'usage'):
            usage = result.usage()
        
        return output, usage, elapsed, tool_info
    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return {"error": f"Timeout after {timeout_seconds}s - the model may be overloaded or the request too complex"}, None, elapsed, {}
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        # Check for context length error
        if "maximum context length" in error_msg.lower() or "8192 tokens" in error_msg or "8302" in error_msg:
            return {
                "error": "Context length exceeded (8192 token limit). This usually happens when the agent makes too many tool calls. Try rephrasing your question more simply."
            }, None, elapsed, {}
        return {"error": error_msg}, None, elapsed, {}


def execute_agent(agent, prompt: str, output_model, agent_name: str):
    """Synchronous wrapper for agent execution."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        output, usage, elapsed, tool_info = loop.run_until_complete(
            run_agent_async(agent, prompt, output_model, agent_name)
        )
        return output, usage, elapsed, tool_info
    finally:
        loop.close()


def format_output(output) -> str:
    """Format output as JSON for display."""
    if hasattr(output, 'model_dump'):
        return json.dumps(output.model_dump(), indent=2, default=str, ensure_ascii=False)
    elif isinstance(output, dict):
        return json.dumps(output, indent=2, default=str, ensure_ascii=False)
    else:
        return str(output)


def format_parsed_output(output) -> str:
    """Format output as human-readable markdown."""
    if hasattr(output, 'model_dump'):
        data = output.model_dump()
    elif isinstance(output, dict):
        data = output
    else:
        return str(output)
    
    # Format based on content
    md = "## Results\n\n"
    
    for key, value in data.items():
        if key.startswith("_"):  # Skip metadata
            continue
        
        # Format key as title
        title = key.replace("_", " ").title()
        
        if isinstance(value, (int, float)):
            # Numeric values
            if abs(value) > 1000:
                md += f"**{title}:** {value:,.2f}\n\n"
            else:
                md += f"**{title}:** {value:.4f}\n\n"
        elif isinstance(value, list):
            # Lists
            md += f"**{title}:**\n"
            for item in value:
                md += f"- {item}\n"
            md += "\n"
        elif isinstance(value, dict):
            # Nested dicts
            md += f"**{title}:**\n"
            for k, v in value.items():
                md += f"- {k}: {v}\n"
            md += "\n"
        else:
            # Strings
            md += f"**{title}:** {value}\n\n"
    
    return md


def format_metrics(elapsed: float, usage, tool_info: Dict) -> str:
    """Format metrics as HTML - compact vertical layout for left sidebar."""
    tokens = usage.total_tokens if usage else 0
    speed = tokens / elapsed if elapsed > 0 and tokens > 0 else 0
    tool_html = format_tool_usage_html(tool_info)
    
    return f"""
    <div style='padding: 10px; background: #f3f4f6; border-radius: 6px; font-family: system-ui; font-size: 13px;'>
        <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
            <span style='color: #6b7280;'>Latency</span>
            <span style='font-weight: 600;'>{elapsed:.2f}s</span>
        </div>
        <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
            <span style='color: #6b7280;'>Tokens</span>
            <span style='font-weight: 600;'>{tokens}</span>
        </div>
        <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
            <span style='color: #6b7280;'>Speed</span>
            <span style='font-weight: 600;'>{speed:.1f} t/s</span>
        </div>
        <div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;'>
            {tool_html}
        </div>
    </div>
    """


# ============================================================================
# AGENT RUNNERS
# ============================================================================

def run_agent_1(prompt: str):
    from examples.agent_1 import agent_1, Portfolio
    output, usage, elapsed, tool_info = execute_agent(agent_1, prompt, Portfolio, "Agent 1")
    
    if isinstance(output, dict) and "error" in output:
        return output["error"], "", "", "Error"
    
    # Store complete result with metadata
    complete_result = output.model_dump() if hasattr(output, 'model_dump') else output
    if isinstance(complete_result, dict):
        complete_result["_metadata"] = {
            "tool_calls": tool_info.get("count", 0),
            "elapsed": elapsed
        }
    
    results_store["Agent 1"] = complete_result
    print(f"[DEBUG] Stored Agent 1 result. results_store now has {len(results_store)} entries: {list(results_store.keys())}")
    
    return format_parsed_output(output), format_output(output), format_metrics(elapsed, usage, tool_info), f"Success ({elapsed:.2f}s)"


def run_agent_2(prompt: str):
    """Run Agent 2 with automatic fallback to Llama 70B on context explosion."""
    from examples.agent_2_wrapped import run_agent_2_wrapped, select_tool_from_question, FinancialCalculationResult
    from examples.agent_2_compliance import validate_calculation
    from app.mitigation_strategies import ToolCallDetector
    from pydantic_ai import Agent, ModelSettings
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider
    
    ready, msg = is_backend_ready("Agent 2")
    if not ready:
        return msg, "", "", "Error"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fallback_used = False
    
    try:
        start = time.time()
        # Try with Koyeb (Qwen 8B) first
        try:
            result = loop.run_until_complete(run_agent_2_wrapped(prompt))
            elapsed = time.time() - start
        except Exception as qwen_error:
            error_msg = str(qwen_error)
            # Check for context length error
            if "maximum context length" in error_msg.lower() or any(tok in error_msg for tok in ["8192", "8300", "8369", "8400"]):
                # Fallback to Llama 70B
                fallback_used = True
                settings = Settings()
                llmpro_model = OpenAIChatModel(
                    model_name=ENDPOINTS.get("llm_pro_finance", {}).get("model", "DragonLLM/llama3.1-70b-fin-v1.0-fp8"),
                    provider=OpenAIProvider(
                        base_url=f"{settings.llm_pro_finance_url}/api",
                        api_key=settings.llm_pro_finance_key,
                    ),
                )
                
                tool = select_tool_from_question(prompt)
                llama_agent = Agent(
                    llmpro_model,
                    model_settings=ModelSettings(max_output_tokens=300, temperature=0.0),
                    system_prompt="Calc. 1x outil. JSON.",
                    tools=[tool],
                    output_type=FinancialCalculationResult,
                    retries=0,
                )
                
                start = time.time()
                result = loop.run_until_complete(llama_agent.run(prompt))
                elapsed = time.time() - start
            else:
                raise  # Re-raise if not context error
        
        # Common result processing
        output = result.output
        tool_calls = ToolCallDetector.extract_tool_calls(result) or []
        
        # Format tool calls
        tool_calls_formatted = []
        for tc in tool_calls:
            name = tc.get('name', 'unknown')
            args = tc.get('args', {})
            args_str = ', '.join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
            tool_calls_formatted.append(f"{name}({args_str})")
        
        # Validation
        is_compliant, compliance_verdict, compliance_details = validate_calculation(output, tool_calls_formatted)
        
        # Tool info
        tool_info = {
            "used": len(tool_calls) > 0,
            "count": len(tool_calls),
            "names": list(set(tc.get('name', 'unknown') for tc in tool_calls)),
            "detailed_trace": tool_calls_formatted
        }
        
        # Get usage
        usage = None
        if hasattr(result, 'usage'):
            usage = result.usage()
        
        # Build metrics HTML
        metrics_parts = []
        
        # Add fallback notice if used
        if fallback_used:
            metrics_parts.append("""
            <div style='margin-bottom: 10px; padding: 10px; background: #fef3c7; border-radius: 6px; border-left: 3px solid #f59e0b;'>
                <strong style='font-size: 12px; color: #92400e;'>ℹ️ Fallback to Llama 70B</strong>
                <div style='font-size: 11px; color: #78350f; margin-top: 4px;'>
                    Qwen 8B made too many duplicate tool calls (context overflow).
                    Automatically switched to Llama 70B (more reliable, fewer duplicates).
                </div>
            </div>
            """)
        
        metrics_parts.append(format_metrics(elapsed, usage, tool_info))
        metrics_parts.append(format_detailed_tool_trace(tool_calls_formatted))
        
        compliance = check_agent_compliance("Agent 2", output, tool_info)
        metrics_parts.append(format_compliance_html(compliance))
        
        metrics_parts.append(f"""
        <div style='margin-top: 10px; padding: 10px; background: #f0f9ff; border-radius: 6px; border-left: 3px solid #3b82f6;'>
            <strong style='font-size: 12px; color: #374151;'>Calculation Verification:</strong>
            <div style='font-size: 11px; color: #6b7280; margin-top: 4px;'>{compliance_verdict}</div>
        </div>
        """)
        
        # Store complete result with metadata for judge agent
        complete_result = output.model_dump() if hasattr(output, 'model_dump') else output
        if isinstance(complete_result, dict):
            complete_result["_metadata"] = {
                "tool_calls": len(tool_calls_formatted),
                "compliance": compliance_verdict,
                "elapsed": elapsed,
                "model_used": "Llama 70B" if fallback_used else "Qwen 8B",
                "fallback": fallback_used
            }
        
        results_store["Agent 2"] = complete_result
        print(f"[DEBUG] Stored Agent 2 result. Keys: {list(complete_result.keys()) if isinstance(complete_result, dict) else 'not a dict'}")
        
        model_used = "Llama 70B" if fallback_used else "Qwen 8B"
        return format_parsed_output(output), format_output(output), "".join(metrics_parts), f"Success with {model_used} ({elapsed:.2f}s)"
        
    except Exception as e:
        return f"Error: {str(e)[:200]}", "", "", "Error"
    finally:
        loop.close()


def run_agent_3(prompt: str):
    from examples.agent_3 import risk_analyst, tax_advisor, AnalyseRisque, AnalyseFiscale
    
    ready, msg = is_backend_ready("Agent 3")
    if not ready:
        return msg, "", "", "Error"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        start = time.time()
        risk_result = loop.run_until_complete(risk_analyst.run(prompt, output_type=AnalyseRisque))
        tax_result = loop.run_until_complete(tax_advisor.run(prompt, output_type=AnalyseFiscale))
        elapsed = time.time() - start
        
        output = {
            "risk_analysis": risk_result.output.model_dump() if hasattr(risk_result.output, 'model_dump') else risk_result.output,
            "tax_analysis": tax_result.output.model_dump() if hasattr(tax_result.output, 'model_dump') else tax_result.output
        }
        
        # Extract tool usage from both agents
        risk_tool_info = extract_tool_usage(risk_result)
        tax_tool_info = extract_tool_usage(tax_result)
        
        # Combine tool usage
        combined_tool_info = {
            "used": risk_tool_info["used"] or tax_tool_info["used"],
            "count": risk_tool_info["count"] + tax_tool_info["count"],
            "names": list(set(risk_tool_info["names"] + tax_tool_info["names"]))
        }
        
        # Combine usage
        tokens = 0
        if hasattr(risk_result, 'usage'):
            tokens += risk_result.usage().total_tokens
        if hasattr(tax_result, 'usage'):
            tokens += tax_result.usage().total_tokens
        
        # Create mock usage object
        class Usage:
            total_tokens = tokens
        
        # Compliance check
        compliance = check_agent_compliance("Agent 3", output, combined_tool_info)
        compliance_html = format_compliance_html(compliance)
        
        results_store["Agent 3"] = output
        metrics_html = format_metrics(elapsed, Usage(), combined_tool_info) + compliance_html
        return format_parsed_output(output), format_output(output), metrics_html, f"Success ({elapsed:.2f}s)"
    except Exception as e:
        return str(e), "", "", "Error"
    finally:
        loop.close()


def run_agent_4(prompt: str):
    """Run Agent 4 with compliance checking and detailed tool trace."""
    from examples.agent_4_compliance import run_with_compliance
    from examples.agent_4 import OptionPricingResult
    import time
    
    ready, msg = is_backend_ready("Agent 4")
    if not ready:
        return msg, "", "", "Error"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        start = time.time()
        response, tool_calls, compliance_verdict = loop.run_until_complete(
            run_with_compliance(prompt)
        )
        elapsed = time.time() - start
        
        # Parse the response to get structured output
        try:
            import json
            # Try to extract JSON from response
            if isinstance(response, str):
                # Try to parse as JSON
                try:
                    output_data = json.loads(response)
                    output = OptionPricingResult(**output_data)
                except:
                    # If not JSON, try to find JSON in the text
                    from app.mitigation_strategies import JSONValidator
                    json_data = JSONValidator.extract_json_from_text(response)
                    if json_data:
                        output = OptionPricingResult(**json_data)
                    else:
                        # Fallback: try to extract from the response text
                        # OptionPricingResult has specific fields, so we'll create a minimal one
                        output = OptionPricingResult(
                            option_price=0.0,
                            delta=0.0,
                            gamma=0.0,
                            vega=0.0,
                            theta=0.0,
                            input_parameters={},
                            calculation_method="unknown",
                            greeks_explanations={}
                        )
            else:
                output = response
        except Exception as e:
            # Fallback if parsing fails
            output = OptionPricingResult(
                option_price=0.0,
                delta=0.0,
                gamma=0.0,
                vega=0.0,
                theta=0.0,
                input_parameters={},
                calculation_method="error",
                greeks_explanations={}
            )
        
        # Extract detailed tool usage
        tool_info = {
            "used": len(tool_calls) > 0,
            "count": len(tool_calls),
            "names": list(set(tc.split('(')[0] for tc in tool_calls if '(' in tc)),
            "detailed_trace": tool_calls  # Store full trace
        }
        
        # Create detailed tool trace HTML
        tool_trace_html = format_detailed_tool_trace(tool_calls)
        
        # Compliance check
        compliance = check_agent_compliance("Agent 4", output, tool_info)
        compliance_html = format_compliance_html(compliance)
        
        # Add compliance verdict from agent_4_compliance
        compliance_verdict_html = f"""
        <div style='margin-top: 10px; padding: 10px; background: #f0f9ff; border-radius: 6px; border-left: 3px solid #3b82f6;'>
            <strong style='font-size: 12px; color: #374151;'>Compliance Agent Verdict:</strong>
            <div style='font-size: 11px; color: #6b7280; margin-top: 4px;'>{compliance_verdict}</div>
        </div>
        """
        
        # Mock usage object
        class Usage:
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
        
        # Store complete result with all Greeks for judge agent
        complete_result = output.model_dump() if hasattr(output, 'model_dump') else output
        results_store["Agent 4"] = complete_result
        
        # Add metadata for judge
        if isinstance(complete_result, dict):
            complete_result["_metadata"] = {
                "tool_calls": len(tool_calls),
                "compliance": compliance_verdict,
                "elapsed": elapsed
            }
        
        print(f"[DEBUG] Stored Agent 4 result with Greeks: {list(complete_result.keys()) if isinstance(complete_result, dict) else 'not a dict'}")
        
        metrics_html = format_metrics(elapsed, Usage(), tool_info) + tool_trace_html + compliance_html + compliance_verdict_html
        return format_parsed_output(output), format_output(output), metrics_html, f"Success ({elapsed:.2f}s)"
    except Exception as e:
        return f"Error: {str(e)}", "", "", "Error"
    finally:
        loop.close()


def run_agent_5_convert(prompt: str):
    """Run Agent 5 - Message Conversion."""
    try:
        from examples.agent_5 import agent_5
        # Agent 5 operations can be complex - use longer timeout (120s)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            output, usage, elapsed, tool_info = loop.run_until_complete(
                run_agent_async(agent_5, prompt, None, "Agent 5 - Convert", timeout_seconds=120.0)
            )
        finally:
            loop.close()
        
        if isinstance(output, dict) and "error" in output:
            return output["error"], "", "", "Error"
        
        # Store complete result with metadata
        complete_result = output.model_dump() if hasattr(output, 'model_dump') else {"output": str(output), "raw": str(output)}
        if isinstance(complete_result, dict):
            complete_result["_metadata"] = {
                "tool_calls": tool_info.get("count", 0),
                "elapsed": elapsed,
                "tools_used": tool_info.get("names", [])
            }
        
        results_store["Agent 5 - Convert"] = complete_result
        print(f"[DEBUG] Stored Agent 5-Convert result. Type: {type(complete_result)}")
        
        return format_parsed_output(output), format_output(output), format_metrics(elapsed, usage, tool_info), f"Success ({elapsed:.2f}s)"
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Agent 5 Convert failed: {error_msg}")
        return f"Error: {error_msg}", "", "", "Error"


def run_agent_5_validate(prompt: str):
    """Run Agent 5 - Message Validation."""
    from examples.agent_5_validator import agent_5_validator
    output, usage, elapsed, tool_info = execute_agent(agent_5_validator, prompt, None, "Agent 5 - Validate")
    
    if isinstance(output, dict) and "error" in output:
        return output["error"], "", "", "Error"
    
    results_store["Agent 5 - Validate"] = output.model_dump() if hasattr(output, 'model_dump') else str(output)
    return format_parsed_output(output), format_output(output), format_metrics(elapsed, usage, tool_info), f"Success ({elapsed:.2f}s)"


def run_agent_5_risk(prompt: str):
    """Run Agent 5 - Risk Assessment."""
    try:
        from examples.agent_5_risk import agent_5_risk
        # Agent 5 Risk operations can be complex - use longer timeout (120s)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            output, usage, elapsed, tool_info = loop.run_until_complete(
                run_agent_async(agent_5_risk, prompt, None, "Agent 5 - Risk", timeout_seconds=120.0)
            )
        finally:
            loop.close()
        
        if isinstance(output, dict) and "error" in output:
            return output["error"], "", "", "Error"
        
        results_store["Agent 5 - Risk"] = output.model_dump() if hasattr(output, 'model_dump') else str(output)
        return format_parsed_output(output), format_output(output), format_metrics(elapsed, usage, tool_info), f"Success ({elapsed:.2f}s)"
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Agent 5 Risk failed: {error_msg}")
        return f"Error: {error_msg}", "", "", "Error"


def run_agent_6(prompt: str):
    """Run judge agent using LLM Pro Finance."""
    from pydantic_ai import Agent, ModelSettings
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider
    from examples.judge_agent import ComprehensiveJudgment
    
    settings = Settings()
    
    # Debug: Check results_store state
    print(f"[DEBUG] results_store keys: {list(results_store.keys())}")
    print(f"[DEBUG] results_store size: {len(results_store)}")
    
    # Check if we have results to judge
    if not results_store:
        debug_msg = f"No results to judge. Run other agents first.\n\nDebug info: results_store has {len(results_store)} entries."
        return debug_msg, "", "", "No data"
    
    # Check backend
    ready, msg = is_backend_ready("Agent 6")
    if not ready:
        return msg, "", "", "Error"
    
    # Create judge model with LLM Pro Finance API path (/api)
    base_url = settings.llm_pro_finance_url
    api_key = settings.llm_pro_finance_key
    model_name = ENDPOINTS.get("llm_pro_finance", {}).get("model", "DragonLLM/llama3.1-70b-fin-v1.0-fp8")
    
    print(f"[DEBUG] Creating judge model:")
    print(f"  Model: {model_name}")
    print(f"  Base URL: {base_url}/api")
    print(f"  API Key: {api_key[:20]}..." if api_key else "  API Key: None")
    
    judge_model = OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url=f"{base_url}/api",  # LLM Pro Finance uses /api
            api_key=api_key,
        ),
    )
    
    judge_agent = Agent(
        judge_model,
        model_settings=ModelSettings(max_output_tokens=3000, temperature=0.3),
        system_prompt="""You are an expert financial AI evaluator. Review agent outputs for:
1. Correctness: Are calculations and extractions accurate?
2. Completeness: Are all required fields present?
3. Quality: Is the output well-structured and professional?

Provide specific, constructive feedback.""",
        output_type=ComprehensiveJudgment,
    )
    
    # Build context from previous results with detailed logging
    print(f"[DEBUG] Building context for judge from {len(results_store)} agent results:")
    for agent_name, result_data in results_store.items():
        if isinstance(result_data, dict):
            fields = list(result_data.keys())
            print(f"  - {agent_name}: {len(fields)} fields: {fields}")
        else:
            print(f"  - {agent_name}: {type(result_data)}")
    
    context = json.dumps(results_store, indent=2, default=str, ensure_ascii=False)
    print(f"[DEBUG] Context size for judge: {len(context)} characters")
    
    full_prompt = f"{prompt}\n\nPrevious agent results:\n{context}"
    
    output, usage, elapsed, tool_info = execute_agent(judge_agent, full_prompt, ComprehensiveJudgment, "Agent 6")
    
    if isinstance(output, dict) and "error" in output:
        return output["error"], "", "", "Error"
    
    results_store["Agent 6"] = output.model_dump() if hasattr(output, 'model_dump') else output
    return format_parsed_output(output), format_output(output), format_metrics(elapsed, usage, tool_info), f"Success ({elapsed:.2f}s)"


# ============================================================================
# UI
# ============================================================================

def create_agent_tab(agent_key: str, run_fn):
    """Create a tab for an agent with improved layout: readable output + JSON."""
    info = AGENT_INFO[agent_key]
    
    gr.Markdown(f"### {info['title']}")
    gr.Markdown(f"*{info['description']}*")
    
    with gr.Row():
        with gr.Column(scale=1):
            input_text = gr.Textbox(
                label="Input",
                value=info["default_input"],
                lines=5,
                placeholder="Enter your prompt..."
            )
            run_btn = gr.Button("Run", variant="primary")
            status = gr.Textbox(label="Status", interactive=False, value="Ready")
            metrics = gr.HTML(label="Metrics", value="<div style='padding: 8px; color: #9ca3af; font-size: 13px;'>Run agent to see metrics</div>")
        
        with gr.Column(scale=2):
            # Human-readable parsed output on top
            parsed_output = gr.Markdown(label="Result", value="*Run agent to see results*")
            # Raw JSON output below
            json_output = gr.Code(label="JSON Output (Full Data)", language="json", lines=10)
    
    run_btn.click(fn=run_fn, inputs=[input_text], outputs=[parsed_output, json_output, metrics, status])


def create_interface():
    with gr.Blocks(title="Open Finance AI") as app:
        
        # Header
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("# Open Finance AI")
                gr.Markdown("Financial analysis with multi-agent systems")
            with gr.Column(scale=1):
                status_html = gr.HTML(value=get_status_html())
                with gr.Row():
                    refresh_btn = gr.Button("Refresh Status", size="sm")
                    wake_btn = gr.Button("Wake Koyeb", size="sm", variant="secondary")
                refresh_btn.click(fn=get_status_html, outputs=status_html)
                wake_msg = gr.Markdown("", visible=True)
                wake_btn.click(
                    fn=wake_up_koyeb,
                    outputs=[status_html, wake_msg]
                )
        
        # Tabs for each agent
        with gr.Tabs():
            with gr.TabItem("Portfolio Extractor"):
                create_agent_tab("Agent 1", run_agent_1)
            
            with gr.TabItem("Financial Calculator"):
                create_agent_tab("Agent 2", run_agent_2)
            
            with gr.TabItem("Risk & Tax Advisor"):
                create_agent_tab("Agent 3", run_agent_3)
            
            with gr.TabItem("Option Pricing"):
                create_agent_tab("Agent 4", run_agent_4)
            
            with gr.TabItem("SWIFT/ISO20022"):
                gr.Markdown("### Complete SWIFT/ISO20022 Message Processing")
                gr.Markdown("Parse, convert, validate, and assess risk for financial messages")
                
                with gr.Tabs():
                    with gr.TabItem("Convert"):
                        gr.Markdown("**Bidirectional conversion:** SWIFT MT ↔ ISO 20022 XML")
                        create_agent_tab("Agent 5 - Convert", run_agent_5_convert)
                    
                    with gr.TabItem("Validate"):
                        gr.Markdown("**Message validation:** Check structure, format, and required fields")
                        create_agent_tab("Agent 5 - Validate", run_agent_5_validate)
                    
                    with gr.TabItem("Risk Assessment"):
                        gr.Markdown("**AML/KYC risk scoring:** Evaluate transaction risk indicators")
                        create_agent_tab("Agent 5 - Risk", run_agent_5_risk)
            
            with gr.TabItem("Judge (70B)"):
                create_agent_tab("Agent 6", run_agent_6)
        
        # Footer with settings info and PydanticAI link
        gr.HTML("""
        <div style='margin-top: 30px; padding: 20px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #6b7280;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <strong>Configuration:</strong> Edit <code style='background: #f3f4f6; padding: 2px 6px; border-radius: 4px;'>.env</code> file to set ENDPOINT, LLM_PRO_FINANCE_URL, LLM_PRO_FINANCE_KEY
                </div>
                <div>
                    Built with <a href="https://ai.pydantic.dev/" target="_blank" style="color: #3b82f6; text-decoration: none;">Pydantic AI</a>
                </div>
            </div>
        </div>
        """)
    
    return app


if __name__ == "__main__":
    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860)
