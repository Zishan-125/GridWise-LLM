from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FiniteNumber = Annotated[float, Field(ge=0)]

class HourInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hour: int
    demand_kwh: FiniteNumber
    solar_kwh: FiniteNumber
    tariff_bdt_per_kwh: FiniteNumber

class BatteryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity_kwh: FiniteNumber
    initial_energy_kwh: FiniteNumber
    minimum_energy_kwh: FiniteNumber
    max_charge_kwh_per_hour: FiniteNumber
    max_discharge_kwh_per_hour: FiniteNumber

    @model_validator(mode="after")
    def valid_state(self):
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError("initial_energy_kwh exceeds capacity_kwh")
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum_energy_kwh exceeds capacity_kwh")
        return self

class OptimizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=256)
    operator_notes: list[str] = Field(min_length=1, max_length=3)
    hours: list[HourInput] = Field(min_length=24, max_length=24)
    battery: BatteryInput

    @field_validator("operator_notes")
    @classmethod
    def notes_nonempty(cls, v):
        if any(not x.strip() for x in v):
            raise ValueError("operator_notes entries must be non-empty")
        return v

    @model_validator(mode="after")
    def hours_are_canonical(self):
        hs = [x.hour for x in self.hours]
        if hs != list(range(24)):
            raise ValueError("hours must contain exactly 0..23 in ascending order")
        return self

class SolarReduction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[int]
    factor: float

class ReserveAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[int]
    minimum_energy_kwh: float

class WindowAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[int]

class GridWindowAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[int]
    max_grid_kwh: float

DirectiveType = Literal[
    "solar_reduction","minimum_battery_reserve","no_charge_window",
    "no_discharge_window","max_grid_window","no_op"
]

class DirectiveInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: dict | None
    explanation: str = Field(default="", max_length=1000)

class HourPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: Literal["charge","discharge","idle"]
    battery_kwh: float
    battery_energy_after_kwh: float

class OptimizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    directive_interpretation: list[DirectiveInterpretation]
    hourly_plan: list[HourPlan]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str
