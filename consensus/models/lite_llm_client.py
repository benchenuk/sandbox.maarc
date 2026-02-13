"""
LiteLLM Client
Unified interface for LLM calls via LangChain (OpenAI-compatible)
"""

import logging
import os
from typing import Any, Dict, Optional

from rich.console import Console

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("consensus.llm")


class LiteLLMClient:
    """
    Unified client for LLM providers.
    Uses LangChain's ChatOpenAI with a proxy endpoint for OpenAI-compatible API.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        proxy_config = config.get("models", {}).get("proxy", {})
        default_model = config.get("models", {}).get("default_model", "gpt-4o")

        self.base_url = proxy_config.get("api_base", os.getenv("OPENAI_BASE_URL", "http://localhost:4000"))
        self.api_key = os.getenv("OPENAI_API_KEY", proxy_config.get("api_key", "EMPTY"))
        self.default_model = default_model

        self._llm = None

    def _get_llm(self, model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
        """Get or create ChatOpenAI instance"""
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=self.base_url,
            api_key=self.api_key,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Make a completion request via LangChain (OpenAI-compatible).

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            model: Model to use (e.g., "gpt-4o", "claude-3-sonnet")
            temperature: Temperature setting
            max_tokens: Max tokens to generate

        Returns:
            Generated text response
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available - using mock response")
            return self._mock_completion(prompt, model)

        model = model or self.default_model
        prompt_preview = prompt[:50].replace("\n", " ")

        logger.info(f"API call: model={model}, temp={temperature}, prompt='{prompt_preview}...'")

        llm = self._get_llm(model, temperature, max_tokens)

        messages = []
        if system_prompt:
            from langchain_core.messages import HumanMessage, SystemMessage
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = await llm.agenerate([messages])
            logger.debug(f"Raw response: {response}")
            
            # Handle different response formats
            gen_list = response.generations
            if not gen_list or not gen_list[0]:
                raise ValueError("Empty generations in response")
            
            generation = gen_list[0][0]
            logger.debug(f"Generation object: {generation}, type: {type(generation)}")
            
            # Try multiple extraction methods
            if hasattr(generation, 'text'):
                result = generation.text
            elif isinstance(generation, tuple):
                result = generation[0]
            else:
                result = str(generation)
                
            # Ensure result is a string
            if not isinstance(result, str):
                result = str(result)
                
            result_preview = result[:50].replace("\n", " ")
            logger.info(f"API success: model={model}, response='{result_preview}...'")
            return result
        except Exception as e:
            import traceback
            logger.error(f"API error: model={model}, error={str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: Could not complete request. {str(e)}"

    def _mock_completion(self, prompt: str, model: str) -> str:
        """Mock completion for testing without API keys."""
        return f"""[Mock Response - LangChain not available]

Model: {model}

This is a placeholder response since langchain-openai is not installed.

To use actual LLM calls:
1. Install: pip install langchain-openai
2. Set proxy: http://localhost:4000 in config.yaml

Research Topic: {prompt[:100]}...

The system would generate real research findings when properly configured."""
