from dataclasses import dataclass

@dataclass(frozen=True)
class DirectiveSet:
    solar_factors: tuple[float, ...]
    reserve: tuple[float, ...]
    no_charge: frozenset[int]
    no_discharge: frozenset[int]
    grid_caps: tuple[float|None, ...]
