"""Main FastAPI application entry point."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents import FinanceAnswer, finance_agent
from app.config import settings
from app.utils import extract_answer_from_reasoning, extract_key_terms

app = FastAPI(
    title="Open Finance PydanticAI API",
    description="Open Finance API using PydanticAI for LLM inference",
    version="0.1.0"
)


class QuestionRequest(BaseModel):
    """Request model for finance questions."""
    question: str


class QuestionResponse(BaseModel):
    """Response model for finance questions."""
    answer: str
    confidence: float
    key_terms: list[str]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "ok",
        "service": "Open Finance PydanticAI API",
        "version": "0.1.0",
        "model_source": settings.hf_space_url,
        "model": settings.model_name,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a finance question to the AI agent.
    
    Handles reasoning model responses by extracting the final answer
    from <think> tags.
    """
    try:
        # Run agent with simple text output (reasoning models return text with tags)
        result = await finance_agent.run(request.question)
        
        # Get the raw response text from AgentRunResult
        raw_response = result.output if hasattr(result, 'output') else str(result)
        
        # Extract answer from reasoning tags (<think> tags)
        clean_answer = extract_answer_from_reasoning(str(raw_response))
        
        # Extract key terms from the cleaned answer
        key_terms = extract_key_terms(clean_answer)
        
        # Estimate confidence based on answer quality
        confidence = 0.9 if clean_answer and len(clean_answer) > 50 else 0.7
        
        return QuestionResponse(
            answer=clean_answer,
            confidence=confidence,
            key_terms=key_terms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

