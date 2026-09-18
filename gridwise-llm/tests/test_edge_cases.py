import pytest
from app.api.schemas import BatteryInput
def test_initial_over_capacity():
    with pytest.raises(ValueError): BatteryInput(capacity_kwh=10,initial_energy_kwh=11,minimum_energy_kwh=1,max_charge_kwh_per_hour=1,max_discharge_kwh_per_hour=1)
