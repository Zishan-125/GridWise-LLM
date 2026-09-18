from fastapi import APIRouter, Request, HTTPException
from app.api.schemas import OptimizeRequest, OptimizeResponse
from app.services.optimization_service import OptimizationService
from app.llm.client import LLMError
from app.optimizer.solver import OptimizationError

router=APIRouter()
service=OptimizationService()

@router.get("/health")
async def health():
    return {"status":"ok"}

@router.post("/optimize-energy", response_model=OptimizeResponse)
async def optimize_energy(req: OptimizeRequest):
    try:
        result=await service.optimize(req)
        return OptimizeResponse.model_validate(result)
    except LLMError as e:
        raise HTTPException(status_code=503, detail="operator-note interpretation service unavailable")
    except OptimizationError:
        raise HTTPException(status_code=422, detail="scenario is infeasible under the supplied constraints")
    except ValueError:
        raise HTTPException(status_code=500, detail="controlled optimization failure")
