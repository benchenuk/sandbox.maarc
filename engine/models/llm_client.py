"""
LLM Client
Unified interface for LLM calls via OpenAI-compatible API
Supports any provider with OpenAI-compatible endpoints (LiteLLM, Ollama, etc.)
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Remove global console and basicConfig that write to stdout/stderr
logger = logging.getLogger("engine.llm")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class LLMClient:
    """
    Unified client for LLM providers.
    Uses LangChain's ChatOpenAI with OpenAI-compatible endpoints.
    Works with LiteLLM proxy, Ollama, OpenRouter, or direct OpenAI.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._llm_cache: Dict[str, ChatOpenAI] = {}
        
        # Initialize rate limiter if configured
        self._rate_limiter = self._create_rate_limiter()
    
    def _create_rate_limiter(self) -> Optional[Any]:
        """Create rate limiter based on configuration."""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        # Check if rate limiting is configured
        rate_limit_config = self.config.get("app", {}).get("rate_limit", {})
        if not rate_limit_config.get("enabled", False):
            return None
        
        requests_per_second = rate_limit_config.get("requests_per_second", 1.0)
        check_every_n_seconds = rate_limit_config.get("check_every_n_seconds", 0.1)
        max_bucket_size = rate_limit_config.get("max_bucket_size", 10)
        
        logger.info(f"[dim]Rate limiter enabled: {requests_per_second} req/s[/dim]")
        
        return InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            check_every_n_seconds=check_every_n_seconds,
            max_bucket_size=max_bucket_size,
        )

    def _get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get provider config by name."""
        from engine.utils.config import get_provider_config
        return get_provider_config(self.config, provider_name)

    def _get_connection_params(self, provider_name: str) -> tuple[str, str, str]:
        """
        Get connection parameters for a provider.
        
        Returns:
            Tuple of (base_url, api_key, default_model)
        """
        provider_cfg = self._get_provider_config(provider_name)
        
        base_url = provider_cfg.get("api_base", os.getenv("OPENAI_BASE_URL", "http://localhost:4000"))
        api_key = provider_cfg.get("api_key", os.getenv("OPENAI_API_KEY", "EMPTY"))
        default_model = provider_cfg.get("default_model", "gpt-4o")
        
        return base_url, api_key, default_model

    def _get_llm(self, provider_name: str, model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
        """Get or create ChatOpenAI instance for a specific provider."""
        cache_key = f"{provider_name}:{model}:{temperature}"
        
        if cache_key not in self._llm_cache:
            base_url, api_key, _ = self._get_connection_params(provider_name)
            
            # Build kwargs, including rate limiter if configured
            kwargs = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "base_url": base_url,
                "api_key": api_key,
            }
            
            if self._rate_limiter is not None:
                kwargs["rate_limiter"] = self._rate_limiter
            
            self._llm_cache[cache_key] = ChatOpenAI(**kwargs)
        
        return self._llm_cache[cache_key]

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Any]] = None,
    ) -> str:
        """
        Make a completion request via LangChain (OpenAI-compatible).

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            provider: Provider name (e.g., 'qwen3-4b', 'stepfun'). Uses orchestrator provider if None.
            model: Model to use. Uses provider's default_model if None.
            temperature: Temperature setting
            max_tokens: Max tokens to generate
            tools: Optional list of tools to bind to the LLM

        Returns:
            Generated text response
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available - using mock response")
            return self._mock_completion(prompt, model or "unknown")

        # Determine provider and model
        if provider is None:
            from engine.utils.config import get_orchestrator_provider
            provider, _ = get_orchestrator_provider(self.config)
        
        _, api_key, default_model = self._get_connection_params(provider)
        model = model or default_model
        
        logger.info(f"[dim]API call: model={model}, temp={temperature}[/dim]")

        llm = self._get_llm(provider, model, temperature, max_tokens)
        
        if tools:
            llm = llm.bind_tools(tools)

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            # Recursive tool execution loop (simple 1-level for now)
            max_tool_iters = 3
            current_iter = 0
            
            while current_iter < max_tool_iters:
                response_msg = await llm.ainvoke(messages)
                messages.append(response_msg)
                
                tool_calls = getattr(response_msg, "tool_calls", [])
                if not tool_calls:
                    break
                
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"[cyan]Executing tool:[/cyan] {tool_name} with {tool_args}")
                    
                    # Find and execute tool
                    tool_output = "Error: Tool not found"
                    if tools:
                        for t in tools:
                            if t.name == tool_name:
                                try:
                                    tool_output = t.invoke(tool_args)
                                except Exception as te:
                                    tool_output = f"Error executing tool: {str(te)}"
                                break
                    
                    messages.append(ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call["id"]
                    ))
                
                current_iter += 1

            result = messages[-1].content
            
            if not isinstance(result, str):
                result = str(result)
                
            logger.info(f"[dim]API response: model={model}, chars={len(result)}[/dim]")
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
