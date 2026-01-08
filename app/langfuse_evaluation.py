"""Langfuse evaluation helpers for scoring and comparing agent runs.

Updated for Langfuse v3.x API compatibility (trace() -> start_span()).
"""

import logging
from typing import Any, Dict, List, Optional

from app.langfuse_config import get_langfuse_client

logger = logging.getLogger(__name__)


def score_trace(trace_id: str, scores: Dict[str, float]) -> bool:
    """
    Add scores to a Langfuse trace.
    
    Args:
        trace_id: Langfuse trace ID
        scores: Dictionary of scores (correctness, tool_usage_score, latency_score, overall_score)
                All scores should be between 0.0 and 1.0
        
    Returns:
        True if successful
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        logger.warning("Langfuse not configured")
        return False
    
    try:
        # Add scores using create_score() (Langfuse v3.x API)
        for score_name, score_value in scores.items():
            try:
                langfuse.create_score(
                    trace_id=trace_id,
                    name=score_name,
                    value=score_value,
                )
            except Exception as e:
                logger.debug(f"Failed to add score {score_name}: {e}")
        
        langfuse.flush()
        logger.info(f"Added scores to trace {trace_id}: {scores}")
        return True
        
    except Exception as e:
        logger.error(f"Error scoring trace {trace_id}: {e}", exc_info=True)
        return False


def create_evaluation_run(dataset_name: str, agent_name: str) -> Optional[str]:
    """
    Create an evaluation run in Langfuse.
    
    Args:
        dataset_name: Name of the dataset being evaluated
        agent_name: Name of the agent being evaluated
        
    Returns:
        Run ID (trace_id) if successful, None otherwise
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        logger.warning("Langfuse not configured")
        return None
    
    try:
        # Create a span for the evaluation run (Langfuse v3.x API)
        # start_span() creates a trace implicitly
        span = langfuse.start_span(
            name=f"evaluation_run_{agent_name}",
            metadata={
                "dataset_name": dataset_name,
                "agent_name": agent_name,
                "evaluation_type": "dataset_evaluation",
            },
        )
        
        # Get the trace_id from the span
        trace_id = span.trace_id if hasattr(span, 'trace_id') else span.id
        
        logger.info(f"Created evaluation run for {agent_name} on {dataset_name}: {trace_id}")
        return trace_id
        
    except Exception as e:
        logger.error(f"Error creating evaluation run: {e}", exc_info=True)
        return None


def compare_runs(run_ids: List[str]) -> Dict[str, Any]:
    """
    Compare different agent runs/versions.
    
    Note: Langfuse v3.x doesn't provide direct trace fetching via SDK.
    Use Langfuse UI or API for detailed trace comparison.
    
    Args:
        run_ids: List of trace/run IDs to compare
        
    Returns:
        Comparison results with metrics (limited in SDK, use Langfuse UI for full comparison)
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        logger.warning("Langfuse not configured")
        return {}
    
    try:
        comparison = {
            "run_ids": run_ids,
            "metrics": {},
            "note": "Use Langfuse UI for detailed trace comparison",
        }
        
        # In Langfuse v3.x, trace fetching is primarily done via API/UI
        # The SDK is optimized for writing traces, not reading
        traces = []
        for run_id in run_ids:
            traces.append({
                "id": run_id,
                "url": f"https://cloud.langfuse.com/trace/{run_id}",
            })
        
        comparison["traces"] = traces
        
        logger.info(f"Prepared comparison for {len(run_ids)} runs - view in Langfuse UI")
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing runs: {e}", exc_info=True)
        return {}


def export_evaluation_results(run_id: str) -> Dict[str, Any]:
    """
    Export evaluation results for analysis.
    
    Note: Langfuse v3.x SDK is optimized for writing traces.
    For detailed export, use Langfuse API or UI export features.
    
    Args:
        run_id: Evaluation run ID (trace_id)
        
    Returns:
        Dictionary with evaluation results and Langfuse URL
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        logger.warning("Langfuse not configured")
        return {}
    
    try:
        results = {
            "run_id": run_id,
            "url": f"https://cloud.langfuse.com/trace/{run_id}",
            "note": "Use Langfuse UI or API for detailed trace export",
        }
        
        logger.info(f"Evaluation results available at: {results['url']}")
        return results
        
    except Exception as e:
        logger.error(f"Error exporting evaluation results: {e}", exc_info=True)
        return {}


