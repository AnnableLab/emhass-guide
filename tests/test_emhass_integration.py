import pytest
import yaml
import os
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.script import Script
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from homeassistant.setup import async_setup_component

@pytest.fixture
async def hass():
    """Fixture to provide a test instance of Home Assistant."""
    hass = HomeAssistant(os.getcwd())
    hass.config.location_name = "Test Home"
    hass.config.latitude = 32.87336
    hass.config.longitude = 117.22743
    hass.config.elevation = 0
    hass.config.time_zone = "UTC"
    
    # Setup the recorder integration so we can mock it?
    # Actually, we don't need to fully setup recorder, we just need the service call to succeed
    # or return what we expect if it uses response variables.
    
    yield hass
    await hass.async_stop()

@pytest.fixture
def load_yaml():
    def _load(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return _load

@pytest.mark.asyncio
async def test_emhass_script_execution(hass, load_yaml):
    """Test that the EMHASS script executes correctly and generates the expected payload."""
    
    # 1. Load the script config
    script_config = load_yaml("src/includes/emhass_script.yaml")
    assert "sequence" in script_config
    sequence = script_config["sequence"]
    
    # 2. Validate Schema
    validated_sequence = cv.SCRIPT_SCHEMA(sequence)
    
    # 3. Create Script Object
    script = Script(hass, validated_sequence, "emhass_mpc", "script")
    
    # 4. Mock State (Sensors)
    # We need to match the sensors used in the script
    hass.states.async_set("sensor.sigen_plant_rated_energy_capacity", "10.0")
    hass.states.async_set("sensor.sigen_plant_ess_rated_charging_power", "5.0")
    hass.states.async_set("sensor.sigen_plant_ess_rated_discharging_power", "5.0")
    hass.states.async_set("sensor.sigen_plant_max_active_power", "10.0")
    hass.states.async_set("sensor.sigen_plant_battery_state_of_charge", "50")
    hass.states.async_set("sensor.sigen_plant_consumed_power", "2.5")
    hass.states.async_set("sensor.sigen_plant_pv_power", "3.0")
    hass.states.async_set("sensor.home_general_price", "0.30")
    hass.states.async_set("sensor.home_feed_in_price", "0.08")

    # Mock Forecast Attributes
    # Solcast
    # We use ISO strings for comparison in templates, ensure they match what HA expects
    now = dt_util.now()
    forecast_data = [
        {"period_start": now, "pv_estimate": 2.5},
        {"period_start": now + dt_util.dt.timedelta(hours=1), "pv_estimate": 0.0},
    ]
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_today", "10", {"detailedForecast": forecast_data})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_tomorrow", "10", {"detailedForecast": []})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_day_3", "10", {"detailedForecast": []})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_tomorrow", "10", {"detailedForecast": []})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_day_3", "10", {"detailedForecast": []})
    
    # Amber
    price_forecast_data = [
        {"start_time": dt_util.now().isoformat(), "per_kwh": 0.30},
        {"start_time": (dt_util.now() + dt_util.dt.timedelta(hours=1)).isoformat(), "per_kwh": 0.25},
    ]
    hass.states.async_set("sensor.home_general_forecast", "0.30", {"forecasts": price_forecast_data})
    
    feed_in_forecast_data = [
        {"start_time": dt_util.now().isoformat(), "per_kwh": 0.08},
    ]
    hass.states.async_set("sensor.home_feed_in_forecast", "0.08", {"forecasts": feed_in_forecast_data})

    # 5. Mock Service Calls
    # The script calls:
    # - recorder.get_statistics (returns response)
    # - rest_command.emhass_naive_mpc_optim
    # - rest_command.emhass_publish_data
    
    # Mock recorder.get_statistics response
    async def mock_recorder_service(call):
        # Return structure expected by template: history.statistics[sensor_id] -> list of dicts
        # The script expects response_variable: history
        # And uses history.statistics[sensors.consumed_power]
        
        # NOTE: The script calls it with response_variable="history"
        # The return value of the service call is what gets put into that variable.
        
        # We simulate some history data
        return {
            "statistics": {
                "sensor.sigen_plant_consumed_power": [
                    {
                        "start": (dt_util.now() - dt_util.dt.timedelta(hours=24)).isoformat(),
                        "mean": 1.5 # kW
                    },
                    {
                        "start": (dt_util.now() - dt_util.dt.timedelta(hours=23)).isoformat(),
                        "mean": 2.0
                    }
                ]
            }
        }
    
    hass.services.async_register("recorder", "get_statistics", mock_recorder_service, supports_response=True)

    # Mock rest_command services to capture calls
    captured_calls = []
    async def mock_rest_service(call):
        captured_calls.append(call)
    
    hass.services.async_register("rest_command", "emhass_naive_mpc_optim", mock_rest_service)
    hass.services.async_register("rest_command", "emhass_publish_data", mock_rest_service)

    # 6. Execute Script
    await script.async_run(run_variables={}, context=None)
    
    # 7. Verify
    assert len(captured_calls) == 2
    
    # Check 1st call (MPC Optim)
    call1 = captured_calls[0]
    assert call1.domain == "rest_command"
    assert call1.service == "emhass_naive_mpc_optim"
    assert "payload" in call1.data
    
    # Parse the payload to check content
    import json
    payload1 = json.loads(call1.data["payload"])
    
    # Verify critical fields
    assert payload1["costfun"] == "profit"
    assert payload1["battery_nominal_energy_capacity"] == 10000 # 10.0 * 1000
    assert payload1["soc_init"] == 0.5 # 50 / 100
    
    # Check forecasts were processed
    # pv_power_forecast should contain our mock data
    # Note: The script keys are isoformat strings
    assert "pv_power_forecast" in payload1
    # We round values in the template
    # assert ...
    
    # Check 2nd call (Publish Data)
    call2 = captured_calls[1]
    assert call2.service == "emhass_publish_data"
    payload2 = json.loads(call2.data["payload"])
    
    # This payload contains custom_pv_forecast_id etc configuration
    assert "custom_pv_forecast_id" in payload2
    assert payload2["custom_pv_forecast_id"]["entity_id"] == "sensor.mpc_pv_power"

@pytest.mark.asyncio
async def test_emhass_automation_structure(hass, load_yaml):
    """Test that the automation correctly references the script."""
    automation_config = load_yaml("src/includes/emhass_automation.yaml")
    
    # Automations are list of triggers, conditions, actions
    # The file provided is a single automation definition (dict)
    
    assert automation_config["alias"] == "Generate EMHASS energy plan"
    
    actions = automation_config["actions"]
    assert len(actions) == 1
    
    action = actions[0]
    # Check if it calls the expected script
    assert action["action"] == "script.generate_emhass_energy_plan_mpc"
