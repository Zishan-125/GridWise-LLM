# Lightweight randomized feasibility smoke test.
import random
from app.api.schemas import HourInput,BatteryInput,DirectiveInterpretation
from app.optimizer.solver import solve
from app.optimizer.postprocess import make_plan
from app.guardrails.replay import replay

def test_random_feasible_instances():
    rng=random.Random(7)
    for _ in range(20):
        hours=[HourInput(hour=h,demand_kwh=rng.uniform(5,15),solar_kwh=rng.uniform(0,4),tariff_bdt_per_kwh=rng.uniform(1,10)) for h in range(24)]
        b=BatteryInput(capacity_kwh=30,initial_energy_kwh=15,minimum_energy_kwh=5,max_charge_kwh_per_hour=10,max_discharge_kwh_per_hour=10)
        d=DirectiveInterpretation(note_index=0,applies=False,directive_type="no_op",structured_adjustment=None,explanation="")
        sol=solve(hours,b,[d]); plan=make_plan(sol)
        replay(plan,hours,b,sol["effects"])
