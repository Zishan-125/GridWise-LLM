"""Integration validator for all ten public cases.
Run against a live service. It compares machine-checkable directive semantics and independently
replays each returned schedule; it never uses public case IDs for runtime behavior.
"""
import json, sys, httpx, math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
data=json.loads((BASE/"data/public_samples.json").read_text())
TOL=.01

def close(a,b): return abs(a-b)<=TOL

def effects(case, interpretations):
    b=case["battery"]
    sf=[1.0]*24; reserve=[b["minimum_energy_kwh"]]*24
    nc=set(); nd=set(); caps=[None]*24
    for d in interpretations:
        if not d["applies"]: continue
        a=d["structured_adjustment"]; hs=a["hours"]
        if d["directive_type"]=="solar_reduction":
            for h in hs: sf[h]*=a["factor"]
        elif d["directive_type"]=="minimum_battery_reserve":
            for h in hs: reserve[h]=max(reserve[h],a["minimum_energy_kwh"])
        elif d["directive_type"]=="no_charge_window": nc.update(hs)
        elif d["directive_type"]=="no_discharge_window": nd.update(hs)
        elif d["directive_type"]=="max_grid_window":
            for h in hs: caps[h]=a["max_grid_kwh"] if caps[h] is None else min(caps[h],a["max_grid_kwh"])
    return sf,reserve,nc,nd,caps

def replay(case, response, expected):
    hs=case["hours"]; b=case["battery"]
    sf,reserve,nc,nd,caps=effects(case,expected)
    assert len(response["hourly_plan"])==24
    energy=b["initial_energy_kwh"]; tg=tc=peak=0
    for h,p in enumerate(response["hourly_plan"]):
        assert p["hour"]==h
        g,s,mag,e=p["grid_kwh"],p["solar_used_kwh"],p["battery_kwh"],p["battery_energy_after_kwh"]
        action=p["battery_action"]
        flow=mag if action=="charge" else -mag if action=="discharge" else 0
        assert all(math.isfinite(float(x)) and x>=-TOL for x in (g,s,mag,e))
        assert s <= hs[h]["solar_kwh"]*sf[h]+TOL
        if action=="idle": assert close(mag,0)
        if action=="charge": assert h not in nc and mag<=b["max_charge_kwh_per_hour"]+TOL
        if action=="discharge": assert h not in nd and mag<=b["max_discharge_kwh_per_hour"]+TOL
        assert e>=reserve[h]-TOL and e<=b["capacity_kwh"]+TOL
        assert close(e,energy+flow)
        assert close(g+s-flow,hs[h]["demand_kwh"])
        if caps[h] is not None: assert g<=caps[h]+TOL
        energy=e; tg+=g; tc+=g*hs[h]["tariff_bdt_per_kwh"]; peak=max(peak,g)
    assert close(energy,b["initial_energy_kwh"])
    assert close(response["total_grid_kwh"],tg)
    assert close(response["total_cost_bdt"],tc)
    assert close(response["peak_grid_kwh"],peak)
    assert close(tc,expected_output_cost(case))

def expected_output_cost(case):
    # Public reference cost is used only as a validation oracle.
    return next(c["expected_output"]["total_cost_bdt"] for c in data["cases"] if c["id"]==case["scenario_id"])

with httpx.Client(timeout=30) as c:
    c.get(sys.argv[1]+"/health" if len(sys.argv)>1 else "http://127.0.0.1:8000/health").raise_for_status()
    base=(sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8000")
    for case in data["cases"]:
        expected=case["expected_output"]["directive_interpretation"]
        r=c.post(base+"/optimize-energy",json=case["input"]); r.raise_for_status()
        got=r.json()
        assert got["scenario_id"]==case["scenario_id"]
        actual=got["directive_interpretation"]
        assert len(actual)==len(expected)
        for a,e in zip(actual,expected):
            assert a["note_index"]==e["note_index"]
            assert a["applies"]==e["applies"]
            assert a["directive_type"]==e["directive_type"]
            assert a["structured_adjustment"]==e["structured_adjustment"]
        replay(case["input"],got,expected)
        print(case["id"], "PASS")
