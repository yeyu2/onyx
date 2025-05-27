"""Test script for the Weather Tool."""

import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from onyx.tools.tool_implementations.weather.weather_tool import WeatherTool

def test_weather_tool() -> None:
    """Test the weather tool."""
    print("Testing Weather Tool...")
    
    # Create an instance of the weather tool
    weather_tool = WeatherTool()
    
    # Check tool metadata
    print(f"Tool name: {weather_tool.name}")
    print(f"Tool description: {weather_tool.description}")
    print(f"Tool display name: {weather_tool.display_name}")
    
    # Get tool definition
    tool_definition = weather_tool.tool_definition()
    print(f"Tool definition: {json.dumps(tool_definition, indent=2)}")
    
    # Test running the tool with a location
    location = "San Francisco, CA"
    print(f"\nTesting tool with location: {location}")
    
    # Run the tool
    responses = list(weather_tool.run(location=location))
    
    # Check response
    if responses:
        print("Tool response:")
        response_data = responses[0].response
        print(f"Location: {response_data.location}")
        print(f"Temperature: {response_data.temperature}")
        print(f"Condition: {response_data.condition}")
        print(f"Humidity: {response_data.humidity}")
        
        # Get final result
        final_result = weather_tool.final_result(*responses)
        print(f"\nFinal result: {json.dumps(final_result, indent=2)}")
    else:
        print("No response received from tool.")
    
    print("\nWeather Tool test completed!")


if __name__ == "__main__":
    test_weather_tool() 