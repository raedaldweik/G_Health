"""AI Evaluation APIs — model metrics from held-out data, agent evalset runner, LLM selection, governance."""
from __future__ import annotations

from fastapi import APIRouter

from services import evals

router = APIRouter()


@router.get("/api/evals/model")
def model_eval(threshold: float = 0.12):
    return evals.model_evaluation(threshold)


@router.get("/api/evals/agent")
def agent_eval():
    return {"evalset": evals.evalset(), "results": evals.last_results(), "status": evals.status()}


@router.post("/api/evals/agent/run")
def agent_eval_run(mode: str = "auto"):
    evals.run_agent_evals(mode)
    return evals.status()


@router.get("/api/evals/agent/status")
def agent_eval_status():
    return {"status": evals.status(), "results": evals.last_results()}


@router.get("/api/evals/llm")
def llm():
    return evals.llm_selection()


@router.get("/api/evals/governance")
def gov():
    return {"controls": evals.governance()}
