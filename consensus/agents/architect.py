"""
Architect Agent
Synthesizes findings into coherent designs
"""

from typing import Any, Dict
from consensus.agents.base import BaseAgent, AgentConfig, AgentResponse
from consensus.ui import display_agent_output


class ArchitectAgent(BaseAgent):
    """
    The Architect synthesizes findings into coherent designs.
    It creates structured proposals that incorporate all perspectives.
    """

    def __init__(self, config: AgentConfig, llm_client=None):
        super().__init__(config, llm_client)

    def _build_system_prompt(self) -> str:
        return """You are the Architect, responsible for synthesizing findings into coherent designs.

Your responsibilities:
1. Integrate perspectives from all agents
2. Create structured, practical designs
3. Balance competing requirements
4. Document architectural decisions
5. Ensure feasibility and maintainability

Your output should be practical, well-structured, and ready for implementation.
Consider both technical excellence and business constraints."""

    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """Execute architect task"""
        self._think("Synthesizing findings into a coherent design...")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            context,
            """Synthesize the research findings into a coherent design proposal.

Your output should include:
1. **Architecture Overview**: High-level design structure
2. **Components**: Key components and their responsibilities
3. **Data Flow**: How data moves through the system
4. **Interfaces**: Key APIs and interactions
5. **Technology Stack**: Recommended technologies with rationale
6. **Decision Rationale**: Why these choices over alternatives

Address any conflicts or trade-offs identified by other agents.
Provide specific, actionable recommendations."""

        )

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response

    async def create_design_proposal(
        self,
        topic: str,
        research_findings: str,
        critiques: str,
    ) -> AgentResponse:
        """Create a design proposal based on research and critiques"""
        self._think(f"Creating design proposal for: {topic}")

        system_prompt = self._build_system_prompt()
        user_prompt = f"""Create a detailed design proposal for: {topic}

Research Findings:
{research_findings}

Critiques and Concerns:
{critiques}

Create a comprehensive design that addresses the research while incorporating the critiques.
For each major decision, explain how it addresses the concerns raised.
Structure the proposal for practical implementation."""

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response
