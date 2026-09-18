from pydantic import BaseModel, ConfigDict
from typing import Literal

DirectiveType = Literal[
    "solar_reduction","minimum_battery_reserve","no_charge_window",
    "no_discharge_window","max_grid_window","no_op"
]

class RawInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: dict | None
    explanation: str = ""

class RawInterpretationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interpretations: list[RawInterpretation]
