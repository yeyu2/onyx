import json

import litellm
from sqlalchemy.orm import Session

from onyx.configs.app_configs import AZURE_DALLE_API_KEY
from onyx.db.connector import check_connectors_exist
from onyx.db.document import check_docs_exist
from onyx.db.models import LLMProvider
from onyx.llm.llm_provider_options import ANTHROPIC_PROVIDER_NAME
from onyx.llm.utils import find_model_obj
from onyx.llm.utils import get_model_map
from onyx.natural_language_processing.utils import BaseTokenizer
from onyx.tools.tool import Tool
from onyx.utils.logger import setup_logger

logger = setup_logger()


def explicit_tool_calling_supported(model_provider: str, model_name: str) -> bool:
    # Add debug logging to see what's being passed in
    logger.debug(f"[TOOL_CALLING_DEBUG] Checking tool calling support for provider='{model_provider}', model='{model_name}'")
    
    # Explicitly support newer OpenAI models that should have tool calling
    # but might not be properly configured in LiteLLM model map yet
    openai_tool_calling_models = {
        "o3", "o3-mini", "o3-preview", 
        "o4", "o4-mini",
        "o1", "o1-mini", "o1-preview",
        "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        "gpt-3.5-turbo"
    }
    
    # Explicitly exclude models that don't support function calling
    openai_non_tool_calling_models = {
        "gpt-3.5-turbo-instruct"
    }
    
    if model_provider == "openai":
        logger.debug(f"[TOOL_CALLING_DEBUG] OpenAI provider detected")
        
        # First check if it's explicitly excluded
        if model_name in openai_non_tool_calling_models:
            logger.debug(f"[TOOL_CALLING_DEBUG] Model '{model_name}' is in exclusion list, returning False")
            return False
            
        # Then check if it matches any of our supported models
        for supported_model in openai_tool_calling_models:
            if model_name.startswith(supported_model):
                logger.debug(f"[TOOL_CALLING_DEBUG] Model '{model_name}' matches '{supported_model}', returning True")
                return True
        
        logger.debug(f"[TOOL_CALLING_DEBUG] Model '{model_name}' does not match any explicit OpenAI patterns")
    else:
        logger.debug(f"[TOOL_CALLING_DEBUG] Non-OpenAI provider '{model_provider}', falling back to LiteLLM lookup")
    
    model_map = get_model_map()
    model_obj = find_model_obj(
        model_map=model_map,
        provider=model_provider,
        model_name=model_name,
    )

    model_supports = (
        model_obj.get("supports_function_calling", False) if model_obj else False
    )
    logger.debug(f"[TOOL_CALLING_DEBUG] LiteLLM lookup result: model_supports={model_supports}, model_obj={model_obj}")
    
    # Anthropic models support tool calling, but
    # a) will raise an error if you provide any tool messages and don't provide a list of tools.
    # b) will send text before and after generating tool calls.
    # We don't want to provide that list of tools because our UI doesn't support sequential
    # tool calling yet for (a) and just looks bad for (b), so for now we just treat anthropic
    # models as non-tool-calling.
    final_result = (
        model_supports
        and model_provider != ANTHROPIC_PROVIDER_NAME
        and model_name not in litellm.anthropic_models
    )
    
    logger.debug(f"[TOOL_CALLING_DEBUG] Final result for '{model_provider}/{model_name}': {final_result}")
    return final_result


def compute_tool_tokens(tool: Tool, llm_tokenizer: BaseTokenizer) -> int:
    return len(llm_tokenizer.encode(json.dumps(tool.tool_definition())))


def compute_all_tool_tokens(tools: list[Tool], llm_tokenizer: BaseTokenizer) -> int:
    return sum(compute_tool_tokens(tool, llm_tokenizer) for tool in tools)


def is_image_generation_available(db_session: Session) -> bool:
    providers = db_session.query(LLMProvider).all()
    for provider in providers:
        if provider.provider == "openai":
            return True

    return bool(AZURE_DALLE_API_KEY)


def is_document_search_available(db_session: Session) -> bool:
    docs_exist = check_docs_exist(db_session)
    connectors_exist = check_connectors_exist(db_session)
    return docs_exist or connectors_exist
