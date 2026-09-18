import pytest
from app.llm.models import RawInterpretationBatch, RawInterpretation

def batch(notes):
    return RawInterpretationBatch(interpretations=[
        RawInterpretation(note_index=i,applies=False,directive_type="no_op",structured_adjustment=None,explanation="irrelevant")
        for i in range(len(notes))])

def payload(notes=["routine note"]):
    return {"scenario_id":"T1","operator_notes":notes,
        "hours":[{"hour":h,"demand_kwh":10,"solar_kwh":0,"tariff_bdt_per_kwh":5} for h in range(24)],
        "battery":{"capacity_kwh":100,"initial_energy_kwh":50,"minimum_energy_kwh":10,
                   "max_charge_kwh_per_hour":20,"max_discharge_kwh_per_hour":20}}

@pytest.mark.asyncio
async def test_health(client):
    r=await client.get("/health"); assert r.status_code==200; assert r.json()=={"status":"ok"}

@pytest.mark.asyncio
async def test_optimize_noop(client,fake_service):
    notes=["routine note"]; fake_service(batch(notes))
    r=await client.post("/optimize-energy",json=payload(notes))
    assert r.status_code==200
    body=r.json()
    assert body["scenario_id"]=="T1" and len(body["hourly_plan"])==24

@pytest.mark.asyncio
async def test_invalid_hours(client):
    p=payload(); p["hours"]=p["hours"][:-1]
    r=await client.post("/optimize-energy",json=p); assert r.status_code in (400,422)
