import pytest
import yaml
import os
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.script import Script
from homeassistant.helpers import config_validation as cv

@pytest.fixture
async def hass():
    """Fixture to provide a test instance of Home Assistant."""
    hass = HomeAssistant(os.getcwd())
    yield hass
    await hass.async_stop()

@pytest.fixture
def load_yaml():
    def _load(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return _load

@pytest.mark.asyncio
async def test_battery_automation_logic(hass: HomeAssistant, load_yaml):
    """Test the logic flow of the battery automation."""
    
    # 1. Load automation config
    automation_config = load_yaml("src/includes/battery_automation.yaml")
    actions = automation_config["actions"]
    
    # 2. Validate Schema
    # We treat the actions list as a script sequence for testing purposes
    validated_sequence = cv.SCRIPT_SCHEMA(actions)
    
    # 3. Create Script Object to run the actions
    script = Script(hass, validated_sequence, "battery_autom_script", "script")
    
    # 4. Setup Mock Services to capture calls
    captured_calls = []
    async def mock_service(call):
        captured_calls.append(call)
        
    hass.services.async_register("select", "select_option", mock_service)
    hass.services.async_register("number", "set_value", mock_service)
    
    # 5. Define Test Cases
    # structure: (p_batt_w, p_grid_w, expected_mode, description)
    test_cases = [
        # Case 1: Grid == 0 -> Maximum Self Consumption
        (0, 0, "Maximum Self Consumption", "Grid 0, Batt 0 -> Self Consume"),
        (1000, 0, "Maximum Self Consumption", "Grid 0, Batt + -> Self Consume"),
        (-1000, 0, "Maximum Self Consumption", "Grid 0, Batt - -> Self Consume"),
        
        # Case 2: Batt > 0 (Discharge) -> Command Discharging
        (2000, 100, "Command Discharging (PV First)", "Batt +2000 (Discharge)"),
        
        # Case 2b: Grid < 0 (Export) and Batt == 0 -> Command Discharging (PV First) ???
        # Logic: p_batt > 0 or (p_grid < 0 and p_batt == 0)
        (0, -100, "Command Discharging (PV First)", "Batt 0, Grid -100 (Export) -> Command Discharging"),
        
        # Case 3: Batt < 0 (Charge) -> Command Charging
        (-3000, 100, "Command Charging (PV First)", "Batt -3000 (Charge)"),
        
        # Case 4: Batt == 0 (Standby)
        # Need to ensure p_grid != 0 (otherwise it hits Case 1) 
        # and p_grid >= 0 (otherwise it hits Case 2b)
        # So: p_batt == 0 and p_grid > 0
        (0, 100, "Standby", "Batt 0, Grid +100 (Import) -> Standby"),
    ]
    
    # Set constant mocks
    # Assuming these are in kW as they are passed directly to number.set_value in Case 1
    hass.states.async_set("sensor.sigen_plant_ess_rated_charging_power", "10.0")
    hass.states.async_set("sensor.sigen_plant_ess_rated_discharging_power", "10.0")
    
    for p_batt, p_grid, expected_mode, desc in test_cases:
        # Clear previous calls
        captured_calls.clear()
        
        # Set state
        hass.states.async_set("sensor.mpc_batt_power", str(p_batt))
        hass.states.async_set("sensor.mpc_grid_power", str(p_grid))
        
        print(f"\nRunning Test Case: {desc}")
        
        # Run script
        await script.async_run(run_variables={}, context=None)
        
        # Verify Mode Selection
        # We look for the select.select_option call
        select_calls = [c for c in captured_calls if c.domain == "select" and c.service == "select_option"]
        assert len(select_calls) > 0, f"No select_option call found for case: {desc}"
        
        # The automation sets the mode, we check if it matches expected
        actual_mode = select_calls[0].data["option"]
        assert actual_mode == expected_mode, f"Failed Case: {desc}. Expected {expected_mode}, got {actual_mode}"
        
        # Verify numeric values for specific cases if needed
        number_calls = [c for c in captured_calls if c.domain == "number" and c.service == "set_value"]
        
        if expected_mode == "Command Charging (PV First)":
            # Check if charging limit is set to abs(p_batt_kw)
            # p_batt = -3000 -> 3.0 kW
            expected_val = abs(p_batt / 1000)
            # Find call to sigen_plant_ess_max_charging_limit
            # ServiceCall.data contains the parameters. Target entities are usually in 'entity_id' key within data 
            # if expanded, or we might need to look at context.
            # For script execution, target often ends up in data.
            
            # We just check values for simplicity, as we know we are calling set_value on *some* entity
            # and we expect *one* of them to be the charging limit.
            
            values = []
            for c in number_calls:
                if "value" in c.data:
                    values.append(float(c.data["value"]))
            
            assert expected_val in values, f"Expected charging limit {expected_val} not found in calls {values}"


