import asyncio
import logging
import yaml
import os
import sys

sys.path.append(os.getcwd())

from homeassistant.core import HomeAssistant
from homeassistant.helpers.script import Script
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import template

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

async def main():
    print("Initializing Home Assistant Core...")
    hass = HomeAssistant(os.getcwd())
    
    script_path = "src/includes/emhass_script.yaml"
    print(f"Reading script from {script_path}...")
    
    with open(script_path, "r") as f:
        script_config = yaml.safe_load(f)
    
    if "sequence" not in script_config:
        print("Error: YAML does not contain a 'sequence' key.")
        return

    sequence_config = script_config["sequence"]

    print("Validating script config schema...")
    try:
        # Validate the sequence using the script schema
        validated_sequence = cv.SCRIPT_SCHEMA(sequence_config)
        print("Schema validation successful!")
    except Exception as e:
        print(f"Schema Validation Failed: {e}")
        return

    print("Creating Script object with validated config...")
    try:
        script_obj = Script(
            hass, 
            validated_sequence, 
            "emhass_test_script", 
            "script", 
            running_description="EMHASS Test Run",
            logger=logging.getLogger("test_script")
        )
    except Exception as e:
        print(f"Failed to create script object: {e}")
        return

    print("Script object created successfully!")
    print("-" * 50)
    
    # Mock necessary states
    print("Mocking sensor states...")
    hass.states.async_set("sensor.sigen_plant_rated_energy_capacity", "10.0")
    hass.states.async_set("sensor.sigen_plant_ess_rated_charging_power", "5.0")
    hass.states.async_set("sensor.sigen_plant_ess_rated_discharging_power", "5.0")
    hass.states.async_set("sensor.sigen_plant_max_active_power", "10.0")
    hass.states.async_set("sensor.sigen_plant_battery_state_of_charge", "50")
    hass.states.async_set("sensor.sigen_plant_consumed_power", "2.5")
    hass.states.async_set("sensor.sigen_plant_pv_power", "3.0")
    hass.states.async_set("sensor.home_general_price", "0.30")
    hass.states.async_set("sensor.home_feed_in_price", "0.08")
    
    # Mock forecasts which are attributes
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_today", "10", {"detailedForecast": []})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_tomorrow", "15", {"detailedForecast": []})
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_day_3", "15", {"detailedForecast": []})
    hass.states.async_set("sensor.home_general_forecast", "0.30", {"forecasts": []})
    hass.states.async_set("sensor.home_feed_in_forecast", "0.08", {"forecasts": []})
    
    print("Starting script execution...")
    try:
        await script_obj.async_run(run_variables={}, context=None)
    except Exception as e:
        print(f"\nExecution halted: {e}")
        if "Service not found" in str(e):
             print("(Expected error: Integrations like 'recorder' or 'rest_command' are not loaded in this minimal test)")

    print("-" * 50)
    print("Done.")
    await hass.async_stop()

if __name__ == "__main__":
    asyncio.run(main())
