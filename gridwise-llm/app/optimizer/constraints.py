def build_directive_effects(hours, battery, interpretations):
    solar_factors=[1.0]*24
    reserve=[battery.minimum_energy_kwh]*24
    no_charge=set()
    no_discharge=set()
    caps=[None]*24
    for d in interpretations:
        a=d.structured_adjustment
        if not d.applies or a is None: continue
        hs=a["hours"]
        if d.directive_type=="solar_reduction":
            for h in hs: solar_factors[h] *= a["factor"]
        elif d.directive_type=="minimum_battery_reserve":
            for h in hs: reserve[h]=max(reserve[h], a["minimum_energy_kwh"])
        elif d.directive_type=="no_charge_window": no_charge.update(hs)
        elif d.directive_type=="no_discharge_window": no_discharge.update(hs)
        elif d.directive_type=="max_grid_window":
            for h in hs:
                caps[h]=a["max_grid_kwh"] if caps[h] is None else min(caps[h], a["max_grid_kwh"])
    return solar_factors, reserve, no_charge, no_discharge, caps
