"""
Base Agent Class
Foundation class for all agents in the research system
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from consensus.models.llm_client import LLMClient
from consensus.ui import display_agent_thinking


class AgentConfig(BaseModel):
    """Configuration for an agent"""
    name: str
    role: str
    description: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2000


class AgentResponse(BaseModel):
    """Standard response from an agent"""
    agent_name: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all research agents.
    Each agent has a specific role in the research workflow.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: Optional[LLMClient] = None,
    ):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.llm_client = llm_client
        self._verbose = False

    def set_verbose(self, verbose: bool):
        """Enable or disable verbose output"""
        self._verbose = verbose

    def _think(self, action: str):
        """Display agent thinking (if verbose)"""
        if self._verbose:
            display_agent_thinking(self.name, action)

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute the agent's task.

        Args:
            context: Current research context including:
                - topic: The research topic
                - previous_outputs: Outputs from other agents
                - iteration: Current iteration number
                - state: Current research state

        Returns:
            AgentResponse with the agent's output
        """
        pass

    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent"""
        return f"""You are {self.name}, {self.role}.

{self.description}

Your role is critical to the research process. Provide thoughtful, well-reasoned responses.
Focus on accuracy, practicality, and thorough analysis.
"""

    def _build_user_prompt(self, context: Dict[str, Any], task: str) -> str:
        """Build the user prompt for the LLM"""
        prompt = f"""Research Topic: {context.get('topic', 'No topic specified')}

Current Iteration: {context.get('iteration', 1)}/{context.get('total_iterations', 5)}

Task: {task}

"""
        # Add previous outputs context
        if context.get("previous_outputs"):
            prompt += "\n## Previous Agent Outputs\n"
            for agent_name, output in context["previous_outputs"].items():
                prompt += f"\n### {agent_name}\n{output}\n"

        # Add current state
        if context.get("current_state"):
            prompt += "\n## Current Research State\n"
            for key, value in context["current_state"].items():
                prompt += f"- {key}: {value}\n"

        return prompt

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AgentResponse:
        """Call the LLM with the given prompts"""
        try:
            if self.llm_client is None:
                return AgentResponse(
                    agent_name=self.name,
                    content="",
                    success=False,
                    error="LLM client not initialized",
                )

            response = await self.llm_client.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            return AgentResponse(
                agent_name=self.name,
                content=response,
                metadata={"model": self.config.model},
            )

        except Exception as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, role={self.role})>"
