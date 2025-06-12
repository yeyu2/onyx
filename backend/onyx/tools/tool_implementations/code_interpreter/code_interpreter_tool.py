"""
Code Interpreter Tool for Onyx.

This tool allows the LLM to execute Python code by sending requests to the
code execution sandbox service.
"""
import json
import requests
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

CODE_EXECUTION_RESPONSE_ID = "code_execution_response"

YES_CODE_EXECUTION = "Yes Code Execution"
SKIP_CODE_EXECUTION = "Skip Code Execution"

CODE_EXECUTION_TEMPLATE = f"""
Given the conversation history and a follow up query, determine if the system should call \
a code interpreter tool to execute Python code.
Your default response is {SKIP_CODE_EXECUTION}.

Respond "{YES_CODE_EXECUTION}" if:
- The user is asking to run, execute, or test Python code.
- The user is asking for calculations, data analysis, or mathematical computations.
- The user is asking to create plots, charts, or visualizations.
- The user is asking to process data or perform data science tasks.
- The user mentions programming, coding, algorithms, or debugging.

Conversation History:
{{chat_history}}

If you are at all unsure, respond with {SKIP_CODE_EXECUTION}.
Respond with EXACTLY and ONLY "{YES_CODE_EXECUTION}" or "{SKIP_CODE_EXECUTION}"

Follow Up Input:
{{final_query}}
""".strip()


class CodeInterpreterTool(Tool[None]):
    _NAME = "run_code_interpreter"
    _DISPLAY_NAME = "Code Interpreter"
    _DESCRIPTION = "Execute Python code in a safe sandboxed environment for calculations, data analysis, and visualizations."

    def __init__(
        self, 
        api_url: str = "http://127.0.0.1:8856",
        timeout: int = 300
    ) -> None:
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout

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
                        "code": {
                            "type": "string",
                            "description": (
                                "The Python code to execute. For data analysis tasks, use dataset information "
                                "already provided in the context (structure, columns, data types, samples). "
                                "Write production-ready code that directly addresses the task - do not write "
                                "exploratory code to inspect datasets. Include proper imports, variable "
                                "definitions, and print statements for output. Common libraries like pandas (pd), "
                                "numpy (np), and matplotlib.pyplot (plt) are available. "
                                "For Excel files with datamaps: Use actual column names from the data sheet, not "
                                "descriptive text from datamaps. Extract column names from brackets (e.g., '[hQS3]' → 'hQS3') "
                                "and check for numbered variants (e.g., 'QA4' → 'QA4r1', 'QA4r2')."
                            )
                        },
                        "description": {
                            "type": "string", 
                            "description": (
                                "Brief description of what the code does (optional)"
                            )
                        }
                    },
                    "required": ["code"]
                }
            }
        }

    def check_if_needs_code_execution(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
    ) -> bool:
        history_str = ""
        for message in history[-5:]:  # Use last 5 messages for context
            if hasattr(message, 'content'):
                history_str += f"{message.content}\n"
        
        prompt = CODE_EXECUTION_TEMPLATE.format(
            chat_history=history_str,
            final_query=query,
        )
        use_code_output = message_to_string(llm.invoke(prompt))

        logger.debug(
            f"Evaluated if should use code execution: {use_code_output}"
        )

        return (
            YES_CODE_EXECUTION.split()[0]
        ).lower() in use_code_output.lower()

    def get_args_for_non_tool_calling_llm(
        self,
        query: str,
        history: list[PreviousMessage],
        llm: LLM,
        force_run: bool = False,
    ) -> dict[str, Any] | None:
        if not force_run and not self.check_if_needs_code_execution(query, history, llm):
            return None

        # For non-tool-calling LLMs, we'll ask the LLM to generate the code
        # This is a simple implementation - in practice you might want more sophisticated code extraction
        return {
            "code": "# Code will be generated by LLM\nprint('Hello from code interpreter!')",
            "description": "Generated code for user query"
        }

    def build_tool_message_content(
        self, *args: ToolResponse
    ) -> str | list[str | dict[str, Any]]:
        response = args[0]
        result_data = response.response
        
        if isinstance(result_data, dict):
            if result_data.get("success", False):
                output = result_data.get("output", "")
                execution_time = result_data.get("execution_time", 0)
                
                if output.strip():
                    return f"""Code executed successfully in {execution_time:.3f} seconds.

Output:
{output}"""
                else:
                    return f"Code executed successfully in {execution_time:.3f} seconds. No output produced."
            else:
                error = result_data.get("error", "Unknown error")
                output = result_data.get("output", "")
                
                error_msg = f"Code execution failed with error:\n{error}"
                
                if output.strip():
                    error_msg += f"\n\nPartial output before error:\n{output}"
                    
                return error_msg
        
        # Fallback to JSON if not a dict
        return json.dumps(result_data)

    def _execute_code(self, code: str) -> dict[str, Any]:
        """
        Send code to the execution service API.
        
        Args:
            code: Python code to execute
            
        Returns:
            API response as dictionary
        """
        try:
            url = f"{self.api_url}/execute"
            
            payload = {
                "code": code,
                "language": "python",
                "timeout": self.timeout
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Make HTTP request to sandbox service
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout + 5  # Add buffer to request timeout
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("Code execution timed out")
            return {
                "success": False,
                "output": "",
                "error": f"Code execution timed out after {self.timeout} seconds",
                "execution_time": self.timeout
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to code execution service at {self.api_url}")
            return {
                "success": False,
                "output": "",
                "error": "Cannot connect to code execution service. Please ensure the service is running.",
                "execution_time": 0
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from code execution service: {e}")
            try:
                error_detail = response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            return {
                "success": False,
                "output": "",
                "error": f"Service error: {error_detail}",
                "execution_time": 0
            }
        except Exception as e:
            logger.error(f"Unexpected error during code execution: {e}")
            return {
                "success": False,
                "output": "",
                "error": f"Unexpected error: {str(e)}",
                "execution_time": 0
            }

    def run(
        self, override_kwargs: None = None, **kwargs: str
    ) -> Generator[ToolResponse, None, None]:
        try:
            code = kwargs.get("code")
            description = kwargs.get("description", "")
            
            if not code:
                yield ToolResponse(
                    id=CODE_EXECUTION_RESPONSE_ID,
                    response={
                        "error": "No code provided for execution",
                        "success": False,
                        "output": "",
                        "execution_time": 0
                    }
                )
                return
            
            logger.info(f"Executing code: {description or 'Unnamed code block'}")
            logger.debug(f"Code content: {code[:200]}...")
            
            # Execute the code using the sandbox service
            result = self._execute_code(code)
            
            yield ToolResponse(
                id=CODE_EXECUTION_RESPONSE_ID,
                response=result,
            )
            
        except Exception as e:
            logger.error(f"Error in code execution tool: {e}")
            yield ToolResponse(
                id=CODE_EXECUTION_RESPONSE_ID,
                response={
                    "error": f"Tool error: {str(e)}",
                    "success": False,
                    "output": "",
                    "execution_time": 0
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
        """Build the next prompt with code execution results"""
        logger.debug(f"[CODE_INTERPRETER_DEBUG] build_next_prompt called with using_tool_calling_llm={using_tool_calling_llm}")
        
        code_response = tool_responses[0]
        
        if isinstance(code_response.response, dict):
            result_data = code_response.response
            
            if result_data.get("success", False):
                output = result_data.get("output", "")
                execution_time = result_data.get("execution_time", 0)
                
                if output.strip():
                    execution_info = f"""Code executed successfully in {execution_time:.3f} seconds.

Output:
{output}"""
                else:
                    execution_info = f"Code executed successfully in {execution_time:.3f} seconds. No output produced."
            else:
                error = result_data.get("error", "Unknown error")
                output = result_data.get("output", "")
                
                execution_info = f"Code execution failed with error:\n{error}"
                
                if output.strip():
                    execution_info += f"\n\nPartial output before error:\n{output}"
        else:
            execution_info = str(code_response.response)
        
        logger.debug(f"[CODE_INTERPRETER_DEBUG] Execution info: {execution_info[:200]}...")
        
        if using_tool_calling_llm:
            logger.debug(f"[CODE_INTERPRETER_DEBUG] Using tool-calling LLM flow - appending tool call and result messages")
            # For tool-calling LLMs, append the tool call and result messages
            prompt_builder.append_message(tool_call_summary.tool_call_request)
            prompt_builder.append_message(tool_call_summary.tool_call_result)
            
        else:
            logger.debug(f"[CODE_INTERPRETER_DEBUG] Using non-tool-calling LLM flow - updating user prompt with results")
            # For non-tool-calling LLMs, update the user prompt with execution results
            from langchain_core.messages import HumanMessage
            user_content = prompt_builder.get_user_message_content()
            
            updated_content = f"""Here are the code execution results:

{execution_info}

Now please respond to: {user_content}"""
            
            logger.debug(f"[CODE_INTERPRETER_DEBUG] Updated content: {updated_content[:200]}...")
            prompt_builder.update_user_prompt(HumanMessage(content=updated_content))
        
        logger.debug(f"[CODE_INTERPRETER_DEBUG] build_next_prompt completed")
        return prompt_builder 