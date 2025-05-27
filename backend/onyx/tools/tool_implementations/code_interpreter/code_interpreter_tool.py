"""Code interpreter tool for executing Python code in a secure sandbox."""

import json
import os
from collections.abc import Generator
from typing import Any, Dict, List, Optional, cast

import requests
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from onyx.chat.prompt_builder.answer_prompt_builder import AnswerPromptBuilder
from onyx.llm.interfaces import LLM
from onyx.llm.models import PreviousMessage
from onyx.tools.base_tool import BaseTool
from onyx.tools.message import ToolCallSummary
from onyx.tools.models import ToolResponse
from onyx.utils.logger import setup_logger
from onyx.utils.special_types import JSON_ro

logger = setup_logger()

# Configuration - can be moved to environment variables or config file
CODE_INTERPRETER_URL = os.environ.get("CODE_INTERPRETER_URL", "http://localhost:8765")

# System prompt for code generation
CODE_GENERATION_SYSTEM_PROMPT = """You are a Python code generation assistant. Your task is to generate clean, efficient Python code that:
1. Is focused on working with datasets and data analysis
2. Accomplishes the specific task described by the user
3. Uses only standard data science libraries (pandas, numpy, matplotlib, scikit-learn)
4. Includes clear comments to explain the logic
5. Handles potential errors gracefully
6. Does not include any explanations outside the code
7. NEVER includes markdown backticks (```) - return ONLY valid Python code

Important rules:
- Include ONLY executable Python code in your response
- Do NOT wrap your code in ```python or ``` tags - just provide the raw Python code
- Do NOT provide explanations before or after the code
- Include sufficient comments WITHIN the code to explain what it does
"""

# System prompt for determining if the tool should be used
SHOULD_USE_CODE_INTERPRETER_SYSTEM_PROMPT = """You are a helpful assistant that determines when to use a code interpreter tool.

Analyze the user's query to determine if it requires data analysis, visualization, or manipulation using Python code.

Only respond with "USE_TOOL" if the query clearly requires code interpretation. Otherwise, respond with "DO_NOT_USE_TOOL".

The code interpreter tool should be used when:
1. The user explicitly asks to run code or use Python
2. The user wants to analyze or visualize datasets
3. The user wants to perform calculations or data processing tasks that would be easier with code
4. The user refers to data files, CSV files, or datasets
5. The query involves generating charts, plots, or other visualizations

The code interpreter should NOT be used for:
1. Simple factual questions
2. Questions about definitions or concepts
3. Requests for explanations without data analysis
4. General advice or recommendations
"""

# Response constant
USE_TOOL = "USE_TOOL"
DO_NOT_USE_TOOL = "DO_NOT_USE_TOOL"


class CodeOutput(BaseModel):
    """Model for code execution output."""
    type: str
    data: str


class CodeInterpreterResponse(BaseModel):
    """Response from the code interpreter execution."""
    success: bool
    output: List[CodeOutput]
    error: Optional[str] = None
    execution_time: float


class CodeInterpreterTool(BaseTool):
    """A tool for executing Python code in a secure sandbox."""
    
    _DISPLAY_NAME = "Code Interpreter"
    
    def __init__(self, api_url: Optional[str] = None) -> None:
        """Initialize the code interpreter tool."""
        self.api_url = api_url or CODE_INTERPRETER_URL
    
    @property
    def name(self) -> str:
        return "execute_code"
    
    @property
    def description(self) -> str:
        return "Execute Python code to analyze datasets, create visualizations, or perform calculations."
    
    @property
    def display_name(self) -> str:
        return self._DISPLAY_NAME
    
    def tool_definition(self) -> dict:
        """Return the tool definition for the LLM API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute. Should be valid Python code that can run independently.",
                        }
                    },
                    "required": ["code"],
                }
            }
        }
    
    def build_tool_message_content(self, *args: ToolResponse) -> str | list[str | dict[str, Any]]:
        """Build a message content based on the tool response."""
        response = cast(CodeInterpreterResponse, args[0].response)
        
        # If there was an error, include it
        if not response.success and response.error:
            return f"Error executing code: {response.error}"
        
        # Format the output
        result = []
        for output in response.output:
            if output.type == "stdout":
                result.append(output.data)
            elif output.type == "figure":
                result.append(f"[Generated Figure: {output.data}]")
        
        return "\n".join(result)
    
    def get_args_for_non_tool_calling_llm(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
        force_run: bool = False,
    ) -> dict[str, Any] | None:
        """Get arguments for LLMs that don't support tool calling."""
        if not force_run:
            # Check if the query is asking for code execution
            should_use_result = llm.invoke(
                [
                    SystemMessage(content=SHOULD_USE_CODE_INTERPRETER_SYSTEM_PROMPT),
                    HumanMessage(content=query)
                ]
            )
            if cast(str, should_use_result.content).strip() != USE_TOOL:
                return None
        
        # Generate Python code for the query
        code_result = llm.invoke(
            [
                SystemMessage(content=CODE_GENERATION_SYSTEM_PROMPT),
                HumanMessage(content=f"Generate Python code to address this request: {query}")
            ]
        )
        
        # Extract the code from the response
        generated_code = cast(str, code_result.content).strip()
        
        # Remove any markdown code blocks if present
        if generated_code.startswith("```python"):
            generated_code = generated_code.split("```python", 1)[1]
        if generated_code.startswith("```"):
            generated_code = generated_code.split("```", 1)[1]
        if generated_code.endswith("```"):
            generated_code = generated_code.rsplit("```", 1)[0]
        
        generated_code = generated_code.strip()
        
        return {"code": generated_code}
    
    def run(
        self, override_kwargs: None = None, **kwargs: Any
    ) -> Generator[ToolResponse, None, None]:
        """Run the code interpreter tool."""
        code = kwargs.get("code", "")
        
        if not code:
            yield ToolResponse(
                id="code_interpreter_error",
                response=CodeInterpreterResponse(
                    success=False,
                    output=[CodeOutput(type="stdout", data="No code provided")],
                    error="No code provided",
                    execution_time=0.0
                )
            )
            return
        
        try:
            # Call the code interpreter service API
            response = requests.post(
                f"{self.api_url}/execute",
                json={"code": code},
                timeout=60  # 60 second timeout
            )
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Convert to our internal model
                code_response = CodeInterpreterResponse(
                    success=result_data.get("success", False),
                    output=[
                        CodeOutput(type=output.get("type", "stdout"), data=output.get("data", ""))
                        for output in result_data.get("output", [])
                    ],
                    error=result_data.get("error"),
                    execution_time=result_data.get("execution_time", 0.0)
                )
                
                yield ToolResponse(
                    id="code_interpreter_response",
                    response=code_response
                )
            else:
                # Handle API errors
                error_message = f"Code interpreter service error: {response.status_code} - {response.text}"
                logger.error(error_message)
                
                yield ToolResponse(
                    id="code_interpreter_error",
                    response=CodeInterpreterResponse(
                        success=False,
                        output=[CodeOutput(type="stdout", data=error_message)],
                        error=error_message,
                        execution_time=0.0
                    )
                )
                
        except requests.RequestException as e:
            # Handle request errors (connection issues, timeouts, etc.)
            error_message = f"Failed to connect to code interpreter service: {str(e)}"
            logger.error(error_message)
            
            yield ToolResponse(
                id="code_interpreter_error",
                response=CodeInterpreterResponse(
                    success=False,
                    output=[CodeOutput(type="stdout", data=error_message)],
                    error=error_message,
                    execution_time=0.0
                )
            )
    
    def final_result(self, *args: ToolResponse) -> JSON_ro:
        """Return the final result of the tool."""
        response = cast(CodeInterpreterResponse, args[0].response)
        
        # Convert to a format suitable for storage
        return {
            "success": response.success,
            "output": [output.dict() for output in response.output],
            "error": response.error,
            "execution_time": response.execution_time
        }
    
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