import pytest
from app.api.schemas import HourInput,BatteryInput,DirectiveInterpretation
from app.optimizer.solver import solve
from app.optimizer.postprocess import make_plan
from app.guardrails.replay import replay

def test_replay_rejects_tampering():
    hours=[HourInput(hour=h,demand_kwh=1,solar_kwh=0,tariff_bdt_per_kwh=1) for h in range(24)]
    b=BatteryInput(capacity_kwh=10,initial_energy_kwh=5,minimum_energy_kwh=1,max_charge_kwh_per_hour=2,max_discharge_kwh_per_hour=2)
    d=DirectiveInterpretation(note_index=0,applies=False,directive_type="no_op",structured_adjustment=None,explanation="")
    sol=solve(hours,b,[d]); plan=make_plan(sol); plan[0]["grid_kwh"]+=1
    with pytest.raises(ValueError): replay(plan,hours,b,sol["effects"])
