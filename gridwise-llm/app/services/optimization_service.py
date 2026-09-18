import logging
from app.llm.client import LLMClient, LLMError
from app.guardrails.normalizer import validate_and_normalize
from app.guardrails.replay import replay
from app.optimizer.solver import solve, OptimizationError
from app.optimizer.postprocess import make_plan

log=logging.getLogger(__name__)

class OptimizationService:
    def __init__(self, llm_client=None):
        self.llm=llm_client or LLMClient()

    async def optimize(self, req):
        try:
            raw=await self.llm.interpret(
                [n for n in req.operator_notes],
                [h.model_dump() for h in req.hours]
            )
            directives=validate_and_normalize(raw.interpretations,len(req.operator_notes),req.battery.capacity_kwh)
            solution=solve(req.hours,req.battery,directives)
            plan=make_plan(solution)
            effects=solution["effects"]
            tg,tc,peak=replay(plan,req.hours,req.battery,effects)
            return {
                "scenario_id":req.scenario_id,
                "directive_interpretation":[d.model_dump() for d in directives],
                "hourly_plan":plan,
                "total_grid_kwh":tg,
                "total_cost_bdt":tc,
                "peak_grid_kwh":peak,
                "plan_summary":"Optimized grid cost using available solar and battery flexibility while enforcing all validated operator directives."
            }
        except (LLMError, ValueError, OptimizationError) as e:
            log.warning("optimization failed: %s", type(e).__name__)
            raise
