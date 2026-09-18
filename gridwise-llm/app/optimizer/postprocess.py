def make_plan(solution):
    plan=[]
    for h,(g,s,b,e) in enumerate(zip(solution["grid"],solution["solar"],solution["flow"],solution["energy"])):
        eps=1e-8
        if b > eps: action="charge"; mag=b
        elif b < -eps: action="discharge"; mag=-b
        else: action="idle"; mag=0.0
        plan.append({
            "hour":h,"grid_kwh":max(0.0,float(g)),
            "solar_used_kwh":max(0.0,float(s)),
            "battery_action":action,"battery_kwh":float(mag),
            "battery_energy_after_kwh":float(e)
        })
    return plan
