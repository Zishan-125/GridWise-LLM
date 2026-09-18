import math

TOL=0.01

def _close(a,b): return abs(a-b) <= TOL

def replay(plan, hours, battery, effects):
    if len(plan)!=24 or [p["hour"] for p in plan] != list(range(24)):
        raise ValueError("plan must contain hours 0..23")
    energy=battery.initial_energy_kwh
    total_grid=total_cost=0.0
    peak=0.0
    for h,p in enumerate(plan):
        nums=[p["grid_kwh"],p["solar_used_kwh"],p["battery_kwh"],p["battery_energy_after_kwh"]]
        if any(not isinstance(x,(int,float)) or not math.isfinite(float(x)) or x<0 for x in nums):
            raise ValueError(f"invalid numeric output at hour {h}")
        g,s,mag,e=p["grid_kwh"],p["solar_used_kwh"],p["battery_kwh"],p["battery_energy_after_kwh"]
        action=p["battery_action"]
        if action not in {"charge","discharge","idle"}: raise ValueError("invalid battery action")
        if action=="idle" and mag != 0: raise ValueError("idle battery_kwh must be zero")
        flow=mag if action=="charge" else -mag if action=="discharge" else 0
        if action=="charge":
            if h in effects.no_charge or mag > battery.max_charge_kwh_per_hour+TOL: raise ValueError("charge constraint")
        if action=="discharge":
            if h in effects.no_discharge or mag > battery.max_discharge_kwh_per_hour+TOL: raise ValueError("discharge constraint")
        effective=hours[h].solar_kwh*effects.solar_factors[h]
        if s > effective+TOL: raise ValueError("solar overuse")
        if g < -TOL: raise ValueError("negative grid")
        cap=effects.grid_caps[h]
        if cap is not None and g > cap+TOL: raise ValueError("grid cap")
        if e < effects.reserve[h]-TOL or e > battery.capacity_kwh+TOL: raise ValueError("battery bounds")
        if not _close(e, energy+flow): raise ValueError("battery transition")
        if not _close(g+s-flow, hours[h].demand_kwh): raise ValueError("energy balance")
        energy=e
        total_grid+=g
        total_cost+=g*hours[h].tariff_bdt_per_kwh
        peak=max(peak,g)
    if not _close(energy,battery.initial_energy_kwh): raise ValueError("battery neutrality")
    return total_grid,total_cost,peak
