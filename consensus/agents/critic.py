"""
Critic Agent
Challenges assumptions and identifies flaws
"""

from typing import Any, Dict
from consensus.agents.base import BaseAgent, AgentConfig, AgentResponse
from consensus.ui import display_agent_output


class CriticAgent(BaseAgent):
    """
    The Critic (Devil's Advocate) challenges assumptions and identifies flaws.
    It ensures thorough analysis by questioning everything.
    """

    def __init__(self, config: AgentConfig, llm_client=None):
        super().__init__(config, llm_client)

    def _build_system_prompt(self) -> str:
        return """You are the Critic (Devil's Advocate), responsible for challenging assumptions and finding flaws.

Your responsibilities:
1. Question every assumption
2. Identify potential weaknesses and risks
3. Find logical fallacies and gaps in reasoning
4. Challenge conventional wisdom
5. Propose alternative viewpoints

Be constructive but thorough. Your goal is to improve the final output by identifying issues early.
Think like a skeptical reviewer who wants to ensure robustness.
"""

    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """Execute critic task"""
        self._think("Identifying flaws and challenging assumptions...")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            context,
            """Review the current research findings and identify issues.

Your critique should cover:
1. **Assumptions**: What assumptions are being made? Are they valid?
2. **Weaknesses**: What are the potential failure points?
3. **Missing Information**: What gaps exist in the analysis?
4. **Risks**: What could go wrong?
5. **Alternatives**: What other approaches should be considered?
6. **Counterarguments**: What arguments could be made against the current position?

Be specific and provide reasoning for each critique point.
Focus on issues that would impact the quality or feasibility of the solution."""

        )

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response

    async def review_design(self, design: str, topic: str) -> AgentResponse:
        """Review a specific design proposal"""
        self._think(f"Reviewing design for: {topic}")

        system_prompt = self._build_system_prompt()
        user_prompt = f"""Review the following design proposal for: {topic}

Design:
{design}

Provide a critical review covering:
1. Technical soundness
2. Scalability concerns
3. Maintainability issues
4. Potential bottlenecks
5. Security considerations
6. Cost implications

Rate each concern by severity (High/Medium/Low) and provide specific recommendations."""

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response
