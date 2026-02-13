"""
Research Graph
LangGraph-based research workflow orchestration
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from consensus.workflow.state import ResearchState
from consensus.workflow.nodes import ResearchNodes
from consensus.models.lite_llm_client import LiteLLMClient
from consensus.ui import (
    console,
    display_iteration_header,
    display_consensus_reached,
    display_error,
)


class ResearchGraph:
    """
    Main research graph orchestration.
    Manages the multi-agent debate workflow using LangGraph.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_client = LiteLLMClient(config)
        self.nodes = ResearchNodes(config, self.llm_client)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(ResearchState)

        # Add nodes
        workflow.add_node("plan", self._plan_wrapper)
        workflow.add_node("research", self._research_wrapper)
        workflow.add_node("critique", self._critique_wrapper)
        workflow.add_node("architect", self._architect_wrapper)
        workflow.add_node("estimator", self._estimator_wrapper)
        workflow.add_node("evaluate", self._evaluate_wrapper)
        workflow.add_node("report", self._report_wrapper)

        # Set entry point
        workflow.set_entry_point("plan")

        # Add edges
        workflow.add_edge("plan", "research")
        workflow.add_edge("research", "critique")
        workflow.add_edge("critique", "architect")
        workflow.add_edge("architect", "estimator")
        workflow.add_edge("estimator", "evaluate")

        # Conditional edge from evaluate
        workflow.add_conditional_edges(
            "evaluate",
            self._should_continue,
            {
                "continue": "research",
                "report": "report",
                "human_feedback": "plan",
            },
        )

        workflow.add_edge("report", END)

        # Compile with checkpointing
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    async def _plan_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for plan node"""
        return await self.nodes.plan_node(state)

    async def _research_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for research node"""
        display_iteration_header(
            state.current_iteration + 1,
            state.max_iterations,
        )
        return await self.nodes.research_node(state)

    async def _critique_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for critique node"""
        return await self.nodes.critique_node(state)

    async def _architect_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for architect node"""
        return await self.nodes.architect_node(state)

    async def _estimator_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for estimator node"""
        return await self.nodes.estimator_node(state)

    async def _evaluate_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for evaluate node"""
        return await self.nodes.evaluate_node(state)

    def _report_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for report generation"""
        return {"status": "completed"}

    def _should_continue(self, state: ResearchState) -> str:
        """Determine if research should continue"""
        if state.status == "paused":
            return "human_feedback"

        if state.consensus_reached:
            return "report"

        if state.current_iteration >= state.max_iterations:
            return "report"

        return "continue"

    def run(
        self,
        topic: str,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the research workflow.

        Args:
            topic: Research topic or question
            verbose: Enable verbose output

        Returns:
            Dictionary containing the research results
        """
        # Get configuration
        research_config = self.config.get("research", {})
        max_iterations = research_config.get("default_iterations", 5)
        min_iterations = research_config.get("min_iterations", 3)

        # Initialize state
        initial_state = ResearchState(
            topic=topic,
            config=self.config,
            max_iterations=max_iterations,
            min_iterations=min_iterations,
            status="initialized",
            start_time=datetime.now().isoformat(),
        )

        try:
            # Run the graph
            result_state = asyncio.run(self._run_graph(initial_state))
            
            # Convert ResearchState to dict for easier access
            result = result_state.model_dump() if hasattr(result_state, 'model_dump') else result_state

            return {
                "status": "completed",
                "topic": topic,
                "iterations": result.get("current_iteration", 0),
                "consensus_score": result.get("consensus_score", 0),
                "consensus_reached": result.get("consensus_reached", False),
                "iteration_results": result.get("iteration_results", []),
                "final_research": result.get("current_researcher_output", ""),
                "final_critique": result.get("current_critic_output", ""),
                "final_design": result.get("current_architect_output", ""),
                "final_estimate": result.get("current_estimator_output", ""),
                "agreements": result.get("key_agreements", []),
                "conflicts": result.get("unresolved_conflicts", []),
            }

        except Exception as e:
            display_error(f"Research failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _run_graph(self, initial_state: ResearchState) -> ResearchState:
        """Run the graph asynchronously"""
        # Run with proper config including thread_id for checkpointing
        config = {
            "recursion_limit": 100,
            "configurable": {
                "thread_id": "research_session",
            }
        }

        # Use ainvoke to get the final state directly
        final_state = await self.graph.ainvoke(initial_state, config)

        # Return the final state
        if final_state:
            # If it's already a ResearchState, return it
            if isinstance(final_state, ResearchState):
                return final_state
            # If it's a dict, convert to ResearchState
            if isinstance(final_state, dict):
                return ResearchState(**final_state)

        return initial_state
