"""
Graph Nodes
LangGraph node implementations for the research workflow
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from consensus.workflow.state import ResearchState, IterationResult
from consensus.agents import (
    OrchestratorAgent,
    ResearcherAgent,
    CriticAgent,
    ArchitectAgent,
    EstimatorAgent,
)
from consensus.agents.base import AgentConfig
from consensus.models.lite_llm_client import LiteLLMClient
from consensus.ui import (
    display_agent_spawn,
    display_agent_thinking,
    display_iteration_header,
    display_checkpoint,
    prompt_user,
    confirm,
)


class ResearchNodes:
    """Collection of LangGraph nodes for the research workflow"""

    def __init__(
        self,
        config: Dict[str, Any],
        llm_client: Optional[LiteLLMClient] = None,
    ):
        self.config = config
        self.llm_client = llm_client or LiteLLMClient(config)
        self._init_agents()

    def _init_agents(self):
        """Initialize all agents with configuration"""
        model_config = self.config.get("models", {})
        agents_config = model_config.get("agents", {})

        # Default agent configurations
        default_configs = {
            "orchestrator": {
                "name": "Orchestrator",
                "role": "Coordinator",
                "description": "Coordinates the research workflow and evaluates consensus",
                "model": "gpt-4o",
                "temperature": 0.7,
            },
            "researcher": {
                "name": "Researcher",
                "role": "Information Gatherer",
                "description": "Gathers information and documents findings",
                "model": "gpt-4o",
                "temperature": 0.5,
            },
            "critic": {
                "name": "Critic",
                "role": "Devil's Advocate",
                "description": "Challenges assumptions and identifies flaws",
                "model": "gpt-4o",
                "temperature": 0.9,
            },
            "architect": {
                "name": "Architect",
                "role": "Designer",
                "description": "Synthesizes findings into coherent designs",
                "model": "gpt-4o",
                "temperature": 0.3,
            },
            "estimator": {
                "name": "Estimator",
                "role": "Effort Analyst",
                "description": "Analyzes complexity and estimates efforts",
                "model": "gpt-4o",
                "temperature": 0.5,
            },
        }

        # Merge default configs with user configs
        def get_agent_config(agent_name: str) -> AgentConfig:
            default = default_configs.get(agent_name, {})
            user_config = agents_config.get(agent_name, {})
            merged = {**default, **user_config}
            return AgentConfig(**merged)

        # Create agents with proper configs
        self.orchestrator = OrchestratorAgent(
            config=get_agent_config("orchestrator"),
            llm_client=self.llm_client,
        )
        self.researcher = ResearcherAgent(
            config=get_agent_config("researcher"),
            llm_client=self.llm_client,
        )
        self.critic = CriticAgent(
            config=get_agent_config("critic"),
            llm_client=self.llm_client,
        )
        self.architect = ArchitectAgent(
            config=get_agent_config("architect"),
            llm_client=self.llm_client,
        )
        self.estimator = EstimatorAgent(
            config=get_agent_config("estimator"),
            llm_client=self.llm_client,
        )

    async def research_node(self, state: ResearchState) -> Dict[str, Any]:
        """Research node - gather information"""
        display_agent_spawn(self.researcher.name, self.researcher.role)
        display_agent_thinking(self.researcher.name, "Researching topic...")

        context = {
            "topic": state.topic,
            "iteration": state.current_iteration + 1,
            "total_iterations": state.max_iterations,
            "previous_outputs": state.get_previous_outputs(),
            "current_state": state.get_current_state_summary(),
        }

        response = await self.researcher.execute(context)

        return {
            "current_researcher_output": response.content if response.success else "",
            "status": "running",
        }

    async def critique_node(self, state: ResearchState) -> Dict[str, Any]:
        """Critique node - challenge findings"""
        display_agent_spawn(self.critic.name, self.critic.role)
        display_agent_thinking(self.critic.name, "Identifying flaws...")

        context = {
            "topic": state.topic,
            "iteration": state.current_iteration + 1,
            "total_iterations": state.max_iterations,
            "previous_outputs": {"Researcher": state.current_researcher_output},
            "current_state": state.get_current_state_summary(),
        }

        response = await self.critic.execute(context)

        return {
            "current_critic_output": response.content if response.success else "",
            "status": "running",
        }

    async def architect_node(self, state: ResearchState) -> Dict[str, Any]:
        """Architect node - synthesize design"""
        display_agent_spawn(self.architect.name, self.architect.role)
        display_agent_thinking(self.architect.name, "Synthesizing design...")

        context = {
            "topic": state.topic,
            "iteration": state.current_iteration + 1,
            "total_iterations": state.max_iterations,
            "previous_outputs": {
                "Researcher": state.current_researcher_output or "",
                "Critic": state.current_critic_output or "",
            },
            "current_state": state.get_current_state_summary(),
        }

        response = await self.architect.execute(context)

        return {
            "current_architect_output": response.content if response.success else "",
            "status": "running",
        }

    async def estimator_node(self, state: ResearchState) -> Dict[str, Any]:
        """Estimator node - analyze efforts"""
        display_agent_spawn(self.estimator.name, self.estimator.role)
        display_agent_thinking(self.estimator.name, "Estimating efforts...")

        context = {
            "topic": state.topic,
            "iteration": state.current_iteration + 1,
            "total_iterations": state.max_iterations,
            "previous_outputs": {
                "Architect": state.current_architect_output or "",
            },
            "current_state": state.get_current_state_summary(),
        }

        response = await self.estimator.execute(context)

        return {
            "current_estimator_output": response.content if response.success else "",
            "status": "running",
        }

    async def evaluate_node(self, state: ResearchState) -> Dict[str, Any]:
        """Evaluate node - check consensus"""
        display_agent_thinking(
            self.orchestrator.name,
            "Evaluating consensus...",
        )

        agent_outputs = {
            "Researcher": state.current_researcher_output or "",
            "Critic": state.current_critic_output or "",
            "Architect": state.current_architect_output or "",
            "Estimator": state.current_estimator_output or "",
        }

        result = await self.orchestrator.evaluate_consensus(
            agent_outputs=agent_outputs,
            iteration=state.current_iteration + 1,
            max_iterations=state.max_iterations,
        )

        # Create iteration result
        iteration_result = IterationResult(
            iteration=state.current_iteration + 1,
            researcher_output=state.current_researcher_output,
            critic_output=state.current_critic_output,
            architect_output=state.current_architect_output,
            estimator_output=state.current_estimator_output,
            consensus_score=result.get("consensus_score", 0),
            consensus_reached=result.get("consensus_reached", False),
            conflicts=result.get("unresolved_conflicts", []),
            agreements=result.get("key_agreements", []),
        )

        # Human-in-the-loop checkpoint
        hitl_config = self.config.get("human_in_the_loop", {})
        if hitl_config.get("enabled", False) and hitl_config.get("checkpoint_frequency") == "every_cycle":
            if not iteration_result.consensus_reached:
                display_checkpoint(
                    checkpoint_name="Iteration Complete",
                    options=[
                        "Continue to next iteration",
                        "Stop and generate report",
                        "Provide feedback to agents",
                    ],
                    current_state=state.get_current_state_summary(),
                )

                feedback = prompt_user("Your choice (or press Enter to continue)")
                if feedback.strip() == "2":
                    # User wants to stop and generate report - set consensus_reached to exit
                    return {
                        "current_iteration": state.current_iteration + 1,
                        "consensus_score": result.get("consensus_score", 0),
                        "consensus_reached": True,
                        "unresolved_conflicts": result.get("unresolved_conflicts", []),
                        "key_agreements": result.get("key_agreements", []),
                        "iteration_results": [iteration_result],
                        "status": "running",
                    }
                elif feedback.strip():
                    return {
                        "human_feedback": feedback,
                        "status": "paused",
                    }

        return {
            "current_iteration": state.current_iteration + 1,
            "consensus_score": result.get("consensus_score", 0),
            "consensus_reached": result.get("consensus_reached", False),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "key_agreements": result.get("key_agreements", []),
            "iteration_results": [iteration_result],
            "status": "running",
        }

    async def plan_node(self, state: ResearchState) -> Dict[str, Any]:
        """Plan node - create research plan"""
        display_agent_spawn(self.orchestrator.name, self.orchestrator.role)
        display_agent_thinking(self.orchestrator.name, "Creating research plan...")

        agents = [self.researcher, self.critic, self.architect, self.estimator]
        response = await self.orchestrator.create_research_plan(
            topic=state.topic,
            agents=agents,
        )

        # Human-in-the-loop checkpoint - approve plan
        hitl_config = self.config.get("human_in_the_loop", {})
        if hitl_config.get("enabled", False):
            display_checkpoint(
                checkpoint_name="Research Plan",
                options=[
                    "Approve plan and continue",
                    "Modify research focus",
                    "Add specific requirements",
                ],
                current_state={"plan": response.content[:200] + "..."} if response.success else {},
            )

            feedback = prompt_user("Your choice (or press Enter to approve)")
            if feedback.strip():
                return {
                    "human_feedback": feedback,
                    "status": "running",
                }

        return {
            "status": "running",
        }

    def should_continue(self, state: ResearchState) -> str:
        """Determine next step in the graph"""
        if state.status == "paused":
            return "human_feedback"

        if state.consensus_reached or state.current_iteration >= state.max_iterations:
            return "report"

        return "continue"
