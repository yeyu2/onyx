"""A dummy weather API tool that returns fixed temperature data."""

import json
from collections.abc import Generator
from typing import Any
from typing import cast

from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from onyx.chat.prompt_builder.answer_prompt_builder import AnswerPromptBuilder
from onyx.llm.interfaces import LLM
from onyx.llm.models import PreviousMessage
from onyx.tools.base_tool import BaseTool
from onyx.tools.message import ToolCallSummary
from onyx.tools.models import ToolResponse
from onyx.utils.special_types import JSON_ro


class WeatherResponse(BaseModel):
    """Response from the weather API."""
    location: str
    temperature: float
    condition: str
    humidity: int


class WeatherTool(BaseTool):
    """A tool for getting weather information for a location."""
    
    _DISPLAY_NAME = "Weather"
    
    def __init__(self) -> None:
        """Initialize the weather tool."""
        pass
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get the current weather for a specified location."
    
    @property
    def display_name(self) -> str:
        return self._DISPLAY_NAME
    
    def tool_definition(self) -> dict:
        """Return the tool definition for the OpenAI API."""
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
                            "description": "The city and state, e.g. San Francisco, CA",
                        }
                    },
                    "required": ["location"],
                }
            }
        }
    
    def build_tool_message_content(self, *args: ToolResponse) -> str | list[str | dict[str, Any]]:
        """Build a message content based on the tool response."""
        weather_data = cast(WeatherResponse, args[0].response)
        return json.dumps(weather_data.dict())
    
    def get_args_for_non_tool_calling_llm(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
        force_run: bool = False,
    ) -> dict[str, Any] | None:
        """Get arguments for LLMs that don't support tool calling."""
        if not force_run:
            # Check if the query is asking about weather
            weather_check_result = llm.invoke(
                [
                    SystemMessage(content="Determine if this query is asking about weather. Return only 'yes' or 'no'."),
                    HumanMessage(content=query)
                ]
            )
            if cast(str, weather_check_result.content).strip().lower() != "yes":
                return None
        
        # Extract location from query
        location_result = llm.invoke(
            [
                SystemMessage(content="Extract the location from this weather query. Only return the location, nothing else."),
                HumanMessage(content=query)
            ]
        )
        location = cast(str, location_result.content).strip()
        
        return {"location": location}
    
    def run(
        self, override_kwargs: None = None, **kwargs: Any
    ) -> Generator[ToolResponse, None, None]:
        """Run the weather tool."""
        location = kwargs.get("location", "Unknown")
        
        # Always return the same fixed weather data
        weather_data = WeatherResponse(
            location=location,
            temperature=72.5,
            condition="Sunny",
            humidity=45
        )
        
        yield ToolResponse(
            id="weather_tool_response",
            response=weather_data
        )
    
    def final_result(self, *args: ToolResponse) -> JSON_ro:
        """Return the final result of the tool."""
        weather_data = cast(WeatherResponse, args[0].response)
        return weather_data.dict()
    
    def build_next_prompt(
        self,
        prompt_builder: AnswerPromptBuilder,
        tool_call_summary: ToolCallSummary,
        tool_responses: list[ToolResponse],
        using_tool_calling_llm: bool,
    ) -> AnswerPromptBuilder:
        """Build the next prompt based on the tool call summary and responses."""
        return super().build_next_prompt(
            prompt_builder,
            tool_call_summary,
            tool_responses,
            using_tool_calling_llm,
        ) 