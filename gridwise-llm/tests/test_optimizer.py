from app.api.schemas import HourInput,BatteryInput,DirectiveInterpretation
from app.optimizer.solver import solve
from app.optimizer.postprocess import make_plan
from app.guardrails.replay import replay

def scenario():
    hours=[HourInput(hour=h,demand_kwh=10,solar_kwh=0,tariff_bdt_per_kwh=1+h) for h in range(24)]
    b=BatteryInput(capacity_kwh=50,initial_energy_kwh=20,minimum_energy_kwh=5,max_charge_kwh_per_hour=10,max_discharge_kwh_per_hour=10)
    return hours,b
def test_solver_and_replay():
    hours,b=scenario()
    ds=[DirectiveInterpretation(note_index=0,applies=False,directive_type="no_op",structured_adjustment=None,explanation="")]
    sol=solve(hours,b,ds); plan=make_plan(sol)
    assert replay(plan,hours,b,sol["effects"])[0] >= 0
def test_no_discharge_window():
    hours,b=scenario()
    ds=[DirectiveInterpretation(note_index=0,applies=True,directive_type="no_discharge_window",structured_adjustment={"hours":[20,21]},explanation="")]
    sol=solve(hours,b,ds)
    assert all(abs(sol["flow"][h]) < 1e-7 for h in (20,21))
