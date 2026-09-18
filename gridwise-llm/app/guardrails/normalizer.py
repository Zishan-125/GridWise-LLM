import math
from app.llm.models import RawInterpretation
from app.api.schemas import DirectiveInterpretation

ALLOWED = {
    "solar_reduction","minimum_battery_reserve","no_charge_window",
    "no_discharge_window","max_grid_window","no_op"
}

def _finite(x):
    return isinstance(x, (int,float)) and not isinstance(x,bool) and math.isfinite(float(x))

def _hours(value):
    if not isinstance(value, list):
        raise ValueError("hours must be an array")
    if any(isinstance(x,bool) or not isinstance(x,int) for x in value):
        raise ValueError("hours must contain integers")
    if any(x < 0 or x > 23 for x in value):
        raise ValueError("hour outside 0..23")
    if len(set(value)) != len(value):
        raise ValueError("duplicate hours")
    if value != sorted(value):
        raise ValueError("hours must be ascending")
    return value

def validate_and_normalize(raw, note_count, capacity):
    if len(raw) != note_count:
        raise ValueError("exactly one interpretation is required per note")
    out=[]
    seen=set()
    for item in raw:
        if item.note_index in seen or item.note_index < 0 or item.note_index >= note_count:
            raise ValueError("invalid or duplicate note_index")
        seen.add(item.note_index)
        typ=item.directive_type
        if typ not in ALLOWED:
            raise ValueError("unsupported directive type")
        if typ == "no_op":
            if item.applies or item.structured_adjustment is not None:
                raise ValueError("invalid no_op semantics")
            adj=None
        else:
            if not item.applies or not isinstance(item.structured_adjustment, dict):
                raise ValueError("invalid applicable directive semantics")
            adj=dict(item.structured_adjustment)
            hs=_hours(adj.get("hours"))
            if typ == "solar_reduction":
                f=adj.get("factor")
                if not _finite(f) or not 0 <= float(f) <= 1:
                    raise ValueError("invalid solar factor")
                adj={"hours":hs,"factor":float(f)}
            elif typ == "minimum_battery_reserve":
                x=adj.get("minimum_energy_kwh")
                if not _finite(x) or float(x)<0 or float(x)>capacity:
                    raise ValueError("invalid reserve")
                adj={"hours":hs,"minimum_energy_kwh":float(x)}
            elif typ == "max_grid_window":
                x=adj.get("max_grid_kwh")
                if not _finite(x) or float(x)<0:
                    raise ValueError("invalid grid cap")
                adj={"hours":hs,"max_grid_kwh":float(x)}
            else:
                adj={"hours":hs}
        out.append(DirectiveInterpretation(
            note_index=item.note_index, applies=item.applies, directive_type=typ,
            structured_adjustment=adj, explanation=item.explanation[:1000]
        ))
    if seen != set(range(note_count)):
        raise ValueError("missing interpretation")
    return sorted(out, key=lambda x:x.note_index)
