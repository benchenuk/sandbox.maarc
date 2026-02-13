"""
Orchestrator Agent
Coordinates the research workflow and evaluates consensus
"""

from typing import Any, Dict, List
from consensus.agents.base import BaseAgent, AgentConfig, AgentResponse
from consensus.ui import display_agent_output


class OrchestratorAgent(BaseAgent):
    """
    The Orchestrator manages the research workflow.
    It decides when to continue iterations and when consensus is reached.
    """

    def __init__(self, config: AgentConfig, llm_client=None):
        super().__init__(config, llm_client)
        self.consensus_threshold = 0.85

    def _build_system_prompt(self) -> str:
        return """You are the Orchestrator, the central coordinator of the research team.

Your responsibilities:
1. Evaluate the outputs of other agents
2. Determine if consensus has been reached
3. Decide whether to continue iterations or proceed to reporting
4. Synthesize insights from different perspectives

Be objective and analytical. Look for genuine agreement rather than surface-level consensus.
Consider the quality and depth of arguments, not just whether agents agree.
"""

    async def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """Execute orchestrator logic"""
        self._think("Evaluating current research state...")

        # Build the evaluation prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            context,
            """Evaluate the current research state and determine if consensus has been reached.

Provide your assessment in the following format:

1. KEY FINDINGS: What are the main conclusions so far?
2. AGREEMENTS: What points do agents agree on?
3. DISAGREEMENTS: What conflicts remain unresolved?
4. CONSENSUS SCORE: Rate overall consensus from 0-100
5. SHOULD CONTINUE: Yes/No and why

Be honest about disagreements - they often lead to better insights."""

        )

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response

    async def evaluate_consensus(
        self,
        agent_outputs: Dict[str, str],
        iteration: int,
        max_iterations: int,
    ) -> Dict[str, Any]:
        """Evaluate if consensus has been reached"""
        self._think("Evaluating consensus among agents...")

        # Build consensus evaluation prompt
        system_prompt = self._build_system_prompt()
        user_prompt = f"""Analyze the following agent outputs and evaluate consensus:

Iteration: {iteration}/{max_iterations}

"""

        for agent_name, output in agent_outputs.items():
            user_prompt += f"\n### {agent_name}\n{output}\n"

        user_prompt += """

Provide a JSON response:
{{
    "consensus_reached": true/false,
    "consensus_score": 0-100,
    "unresolved_conflicts": ["conflict1", "conflict2"],
    "key_agreements": ["agreement1", "agreement2"],
    "recommendation": "continue/stop"
}}
"""

        response = await self.call_llm(system_prompt, user_prompt)

        if response.success:
            try:
                import json
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except Exception:
                pass

        # Default if parsing fails
        return {
            "consensus_reached": iteration >= 3,
            "consensus_score": 50,
            "unresolved_conflicts": [],
            "key_agreements": [],
            "recommendation": "continue" if iteration < max_iterations else "stop",
        }

    async def create_research_plan(
        self,
        topic: str,
        agents: List[BaseAgent],
    ) -> AgentResponse:
        """Create a research plan"""
        self._think("Creating research plan...")

        agent_names = ", ".join([a.name for a in agents])

        system_prompt = self._build_system_prompt()
        user_prompt = f"""Create a research plan for the following topic:

Topic: {topic}

Available Agents: {agent_names}

For each agent, specify:
1. Their specific task in the research
2. The order of execution
3. What information they should provide

Format your response as a structured plan."""

        response = await self.call_llm(system_prompt, user_prompt)

        if self._verbose and response.success:
            display_agent_output(self.name, response.content)

        return response
