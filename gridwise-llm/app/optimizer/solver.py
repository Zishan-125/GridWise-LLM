import numpy as np
from scipy.optimize import linprog
from .constraints import build_directive_effects
from .model import DirectiveSet

class OptimizationError(RuntimeError):
    pass

def solve(hours, battery, interpretations):
    solar_factor, reserve, no_charge, no_discharge, caps = build_directive_effects(hours,battery,interpretations)
    n=24
    # Variables per hour: grid, solar_used, battery_flow(+charge/-discharge), energy_after.
    # A single signed battery-flow variable makes simultaneous charge/discharge impossible.
    G=np.arange(n)
    S=np.arange(n)+n
    B=np.arange(n)+2*n
    E=np.arange(n)+3*n
    c=np.zeros(4*n)
    for h in range(n): c[G[h]]=hours[h].tariff_bdt_per_kwh
    bounds=[]
    for h in range(n): bounds.append((0, caps[h]))
    for h in range(n): bounds.append((0, hours[h].solar_kwh*solar_factor[h]))
    for h in range(n):
        lo=0 if h in no_discharge else -battery.max_discharge_kwh_per_hour
        hi=0 if h in no_charge else battery.max_charge_kwh_per_hour
        bounds.append((lo,hi))
    for h in range(n): bounds.append((reserve[h], battery.capacity_kwh))

    Aeq=[]; beq=[]
    # grid + solar - battery_flow = demand
    for h in range(n):
        row=np.zeros(4*n); row[G[h]]=1; row[S[h]]=1; row[B[h]]=-1
        Aeq.append(row); beq.append(hours[h].demand_kwh)
    # E_h - E_{h-1} - B_h = 0, with E_-1 = initial
    for h in range(n):
        row=np.zeros(4*n); row[E[h]]=1; row[B[h]]=-1
        rhs=battery.initial_energy_kwh if h==0 else 0
        if h>0: row[E[h-1]]=-1
        Aeq.append(row); beq.append(rhs)
    row=np.zeros(4*n); row[E[23]]=1
    Aeq.append(row); beq.append(battery.initial_energy_kwh)
    res=linprog(c,A_eq=np.asarray(Aeq),b_eq=np.asarray(beq),bounds=bounds,method="highs")
    if not res.success:
        raise OptimizationError(res.message)
    x=res.x
    return {
        "grid":x[G].tolist(), "solar":x[S].tolist(), "flow":x[B].tolist(),
        "energy":x[E].tolist(), "effects":DirectiveSet(tuple(solar_factor),tuple(reserve),
            frozenset(no_charge),frozenset(no_discharge),tuple(caps))
    }
