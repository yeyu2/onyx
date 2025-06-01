import json
from collections.abc import Generator
from typing import Any

from onyx.llm.interfaces import LLM
from onyx.llm.models import PreviousMessage
from onyx.llm.utils import message_to_string
from onyx.tools.message import ToolCallSummary
from onyx.tools.models import ToolResponse
from onyx.tools.tool import Tool
from onyx.utils.logger import setup_logger
from onyx.utils.special_types import JSON_ro

logger = setup_logger()

WEATHER_RESPONSE_ID = "weather_response"

YES_WEATHER_SEARCH = "Yes Weather Search"
SKIP_WEATHER_SEARCH = "Skip Weather Search"

WEATHER_TEMPLATE = f"""
Given the conversation history and a follow up query, determine if the system should call \
a weather tool to get weather information for a location.
Your default response is {SKIP_WEATHER_SEARCH}.

Respond "{YES_WEATHER_SEARCH}" if:
- The user is asking for weather information for a specific location.
- The user is asking about current weather conditions.
- The user is asking about weather forecast.

Conversation History:
{{chat_history}}

If you are at all unsure, respond with {SKIP_WEATHER_SEARCH}.
Respond with EXACTLY and ONLY "{YES_WEATHER_SEARCH}" or "{SKIP_WEATHER_SEARCH}"

Follow Up Input:
{{final_query}}
""".strip()


class WeatherResponse:
    def __init__(self, location: str, temperature: str, condition: str, humidity: str, wind_speed: str):
        self.location = location
        self.temperature = temperature
        self.condition = condition
        self.humidity = humidity
        self.wind_speed = wind_speed


# override_kwargs is not supported for weather tools
class WeatherTool(Tool[None]):
    _NAME = "run_weather"
    _DISPLAY_NAME = "Weather Tool (Test Only)"
    _DESCRIPTION = "Get weather information for a specific location using simulated data."

    def __init__(self) -> None:
        pass

    @property
    def name(self) -> str:
        return self._NAME

    @property
    def description(self) -> str:
        return self._DESCRIPTION

    @property
    def display_name(self) -> str:
        return self._DISPLAY_NAME

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get weather information for",
                        },
                    },
                    "required": ["location"],
                },
            },
        }

    def check_if_needs_weather(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
    ) -> bool:
        history_str = ""
        for message in history[-5:]:  # Use last 5 messages for context
            if hasattr(message, 'content'):
                history_str += f"{message.content}\n"
        
        prompt = WEATHER_TEMPLATE.format(
            chat_history=history_str,
            final_query=query,
        )
        use_weather_output = message_to_string(llm.invoke(prompt))

        logger.debug(
            f"Evaluated if should use weather: {use_weather_output}"
        )

        return (
            YES_WEATHER_SEARCH.split()[0]
        ).lower() in use_weather_output.lower()

    def get_args_for_non_tool_calling_llm(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
        force_run: bool = False,
    ) -> dict[str, Any] | None:
        if not force_run and not self.check_if_needs_weather(query, history, llm):
            return None

        # Extract location from query - simple implementation
        # In a real implementation, you might use NLP to extract location
        location = query.lower()
        if "weather" in location:
            # Try to extract location after "weather in" or "weather for"
            if "weather in " in location:
                location = location.split("weather in ")[-1].strip()
            elif "weather for " in location:
                location = location.split("weather for ")[-1].strip()
            elif "weather at " in location:
                location = location.split("weather at ")[-1].strip()
            else:
                location = "Unknown Location"
        else:
            location = query.strip()

        return {"location": location}

    def build_tool_message_content(
        self, *args: ToolResponse
    ) -> str | list[str | dict[str, Any]]:
        response = args[0]
        return json.dumps(response.response)

    def _get_fake_weather(self, location: str) -> WeatherResponse:
        """Generate fake weather data for any location"""
        # Simple hash-based fake data to ensure consistency
        location_hash = hash(location.lower()) % 1000
        
        # Fake temperature based on location hash
        temp_celsius = 15 + (location_hash % 25)  # 15-40°C
        temp_fahrenheit = int(temp_celsius * 9/5 + 32)
        
        # Fake conditions
        conditions = [
            "Sunny", "Partly Cloudy", "Cloudy", "Light Rain", 
            "Heavy Rain", "Thunderstorms", "Snow", "Foggy", "Windy"
        ]
        condition = conditions[location_hash % len(conditions)]
        
        # Fake humidity
        humidity = 30 + (location_hash % 60)  # 30-90%
        
        # Fake wind speed
        wind_speed = 5 + (location_hash % 20)  # 5-25 km/h
        
        return WeatherResponse(
            location=location.title(),
            temperature=f"{temp_celsius}°C ({temp_fahrenheit}°F)",
            condition=condition,
            humidity=f"{humidity}%",
            wind_speed=f"{wind_speed} km/h"
        )

    def run(
        self, override_kwargs: None = None, **kwargs: str
    ) -> Generator[ToolResponse, None, None]:
        try:
            location = kwargs.get("location", "Unknown Location")
            
            logger.info(f"Getting weather for location: {location}")
            
            weather_data = self._get_fake_weather(location)
            
            weather_dict = {
                "location": weather_data.location,
                "temperature": weather_data.temperature,
                "condition": weather_data.condition,
                "humidity": weather_data.humidity,
                "wind_speed": weather_data.wind_speed,
                "source": "Simulated Weather Data"
            }
            
            yield ToolResponse(
                id=WEATHER_RESPONSE_ID,
                response=weather_dict,
            )
            
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            yield ToolResponse(
                id=WEATHER_RESPONSE_ID,
                response={
                    "error": f"Failed to get weather data: {str(e)}",
                    "location": kwargs.get("location", "Unknown"),
                },
            )

    def final_result(self, *args: ToolResponse) -> JSON_ro:
        return args[0].response

    def build_next_prompt(
        self,
        prompt_builder,
        tool_call_summary: ToolCallSummary,
        tool_responses: list[ToolResponse],
        using_tool_calling_llm: bool,
    ):
        """Build the next prompt with weather data"""
        weather_response = tool_responses[0]
        
        if isinstance(weather_response.response, dict):
            weather_data = weather_response.response
            if "error" in weather_data:
                weather_info = f"Weather data unavailable for {weather_data.get('location', 'unknown location')}: {weather_data['error']}"
            else:
                weather_info = f"""Weather information for {weather_data['location']}:
- Temperature: {weather_data['temperature']}
- Condition: {weather_data['condition']}  
- Humidity: {weather_data['humidity']}
- Wind Speed: {weather_data['wind_speed']}
- Source: {weather_data['source']}"""
        else:
            weather_info = str(weather_response.response)
        
        if using_tool_calling_llm:
            # For tool-calling LLMs, append the tool call and result messages
            prompt_builder.append_message(tool_call_summary.tool_call_request)
            prompt_builder.append_message(tool_call_summary.tool_call_result)
        else:
            # For non-tool-calling LLMs, update the user prompt with weather info
            from langchain_core.messages import HumanMessage
            user_content = prompt_builder.get_user_message_content()
            
            updated_content = f"""Here is the weather information:

{weather_info}

Now please respond to: {user_content}"""
            
            prompt_builder.update_user_prompt(HumanMessage(content=updated_content))
        
        return prompt_builder 