"""
Estimator Agent
Analyzes complexity and estimates efforts
"""

from typing import Any, Dict
from consensus.agents.base import BaseAgent, AgentConfig, AgentResponse
from consensus.ui import display_agent_output


class EstimatorAgent(BaseAgent):
    """
    The Estimator analyzes complexity and estimates efforts.
    It provides realistic assessments of timeline, cost, and resources.
    """

    def __init__(self, config: AgentConfig, llm_client=None):
        super().__init__(config, llm_client)

    def _build_system_prompt(self) -> str:
        return """You are the Estimator, responsible for analyzing complexity and estimating efforts.

Your responsibilities:
1. Assess technical complexity
2. Estimate development efforts
3. Identify potential risks
4. Provide realistic timelines
5. Recommend resource allocation
6. Highlight dependencies

Be realistic and consider various factors that affect effort estimation.
Provide ranges rather than single points when uncertain."""

    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """Execute estimator task"""
        self._think("Analyzing complexity and estimating efforts...")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            context,
            """Analyze the proposed solution and estimate required efforts.

Your analysis should include:
1. **Complexity Assessment**: Technical complexity rating (1-10)
2. **Effort Estimation**:
   - Development time (best/worst/likely case)
   - Team size needed
   - Skill requirements
3. **Risk Assessment**: Key risks with probability and impact
4. **Dependencies**: External dependencies and prerequisites
5. **Phasing**: Recommended implementation phases
6. **Resource Requirements**: Infrastructure, tools, and skills needed

Provide specific estimates with reasoning.
Consider both development and ongoing maintenance efforts."""

        )

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response

    async def estimate_effort(
        self,
        topic: str,
        design: str,
    ) -> AgentResponse:
        """Estimate effort for a specific design"""
        self._think(f"Estimating effort for: {topic}")

        system_prompt = self._build_system_prompt()
        user_prompt = f"""Estimate the effort required to implement the following design:

Topic: {topic}

Design:
{design}

Provide:
1. **T-Shirt Size**: XS/S/M/L/XL/XXL
2. **Estimated Timeline**: weeks/months
3. **Team Composition**: roles and headcount
4. **Key Phases**: major implementation phases
5. **Risk Factors**: items that could increase effort
6. **Mitigation**: how to reduce uncertainty

Use T-shirt sizing for initial estimation:
- XS: 1-2 weeks
- S: 2-4 weeks
- M: 1-2 months
- L: 2-3 months
- XL: 3-6 months
- XXL: 6+ months"""

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response
