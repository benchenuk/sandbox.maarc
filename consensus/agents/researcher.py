"""
Researcher Agent
Gathers information and documents findings
"""

from typing import Any, Dict
from consensus.agents.base import BaseAgent, AgentConfig, AgentResponse
from consensus.ui import display_agent_output


class ResearcherAgent(BaseAgent):
    """
    The Researcher gathers information about the topic.
    It documents findings, collects relevant data, and provides factual context.
    """

    def __init__(self, config: AgentConfig, llm_client=None):
        super().__init__(config, llm_client)

    def _build_system_prompt(self) -> str:
        return """You are the Researcher, responsible for gathering and documenting information.

Your responsibilities:
1. Research the topic thoroughly
2. Document key findings and facts
3. Provide relevant context and background
4. Cite best practices and established patterns
5. Be objective and evidence-based

Focus on factual accuracy and comprehensive coverage.
Provide specific details, patterns, and proven approaches.
"""

    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """Execute researcher task"""
        self._think("Researching the topic...")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            context,
            """Research the given topic and provide comprehensive findings.

Your output should include:
1. **Key Concepts**: Core ideas and definitions
2. **Best Practices**: Proven approaches and patterns
3. **Common Patterns**: Widely adopted solutions
4. **Trade-offs**: Advantages and disadvantages of different approaches
5. **Recommendations**: Suggested approaches based on the context

Be thorough and provide specific, actionable information.
Consider multiple perspectives and approaches."""

        )

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response

    async def gather_initial_assessment(self, topic: str) -> AgentResponse:
        """Perform initial research on the topic"""
        self._think(f"Performing initial research on: {topic}")

        system_prompt = self._build_system_prompt()
        user_prompt = f"""Provide an initial research assessment for the following topic:

Topic: {topic}

Cover:
1. What are the key technical considerations?
2. What are the main design decisions to make?
3. What are the potential challenges?
4. What are the success criteria?

Provide a structured overview that other agents can build upon."""

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response
