import asyncio
import logging
import os
import sys
import jinja2

sys.path.append(os.getcwd())

from homeassistant.core import HomeAssistant
from homeassistant.helpers import template

logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

async def main():
    print("Initializing Home Assistant Core...")
    hass = HomeAssistant(os.getcwd())
    
    # We need to manually inspect the TemplateEnvironment to see what filters are loaded
    # The TemplateEnvironment is created inside the Template helper
    
    print("\nChecking registered filters in a fresh Template environment...")
    # Create a dummy template to trigger environment creation
    tpl = template.Template("{{ 1 + 1 }}", hass)
    
    # Access the environment (this might require some internal access if it's private)
    # In recent HA versions, the environment is attached to the template instance or hass.data
    
    try:
        # Try to render something that uses 'combine'
        tpl_combine = template.Template("{{ {'a': 1} | combine({'b': 2}) }}", hass)
        result = tpl_combine.async_render()
        print(f"Render result: {result}")
        print("SUCCESS: 'combine' filter is available!")
    except Exception as e:
        print(f"Render failed: {e}")
        print("FAILURE: 'combine' filter is NOT available.")
        
    # Let's try to define it manually to show how it works
    def combine(dict1, dict2):
        return {**dict1, **dict2}
        
    print("\nExplanation:")
    print("The 'combine' filter is not a standard Jinja2 filter.")
    print("It is likely added by Home Assistant during the 'frontend' or 'template' integration setup.")
    print("Since we are only running the Core without loading all default integrations, it is missing.")

    await hass.async_stop()

if __name__ == "__main__":
    asyncio.run(main())

