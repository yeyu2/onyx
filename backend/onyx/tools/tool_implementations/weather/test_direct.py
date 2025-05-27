"""Simple direct test for the Weather Tool."""

import json
from weather_tool import WeatherTool

def main():
    # Create the tool
    weather_tool = WeatherTool()
    
    # Print basic info
    print(f"Tool name: {weather_tool.name}")
    print(f"Tool description: {weather_tool.description}")
    
    # Get the tool definition
    tool_def = weather_tool.tool_definition()
    print(f"Tool definition: {json.dumps(tool_def, indent=2)}")
    
    # Run the tool with a location
    responses = list(weather_tool.run(location="New York"))
    
    # Print the response
    if responses:
        response = responses[0].response
        print(f"\nResponse for New York:")
        print(f"Temperature: {response.temperature}°F")
        print(f"Condition: {response.condition}")
        print(f"Humidity: {response.humidity}%")
    else:
        print("No response received")

if __name__ == "__main__":
    main() 