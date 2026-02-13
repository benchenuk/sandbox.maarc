"""
Research State Definitions
Pydantic models for LangGraph state management
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    """Output from a single agent"""
    agent_name: str
    content: str
    iteration: int
    timestamp: str = ""


class IterationResult(BaseModel):
    """Result from a single iteration"""
    iteration: int
    researcher_output: Optional[str] = None
    critic_output: Optional[str] = None
    architect_output: Optional[str] = None
    estimator_output: Optional[str] = None
    consensus_score: float = 0.0
    consensus_reached: bool = False
    conflicts: List[str] = Field(default_factory=list)
    agreements: List[str] = Field(default_factory=list)


class ResearchState(BaseModel):
    """
    State object for the research workflow.
    Passed between nodes in the LangGraph.
    """

    # Topic and configuration
    topic: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)

    # Iteration tracking
    current_iteration: int = 0
    max_iterations: int = 5
    min_iterations: int = 3

    # Research outputs
    research_findings: List[str] = Field(default_factory=list)
    critiques: List[str] = Field(default_factory=list)
    designs: List[str] = Field(default_factory=list)
    estimates: List[str] = Field(default_factory=list)

    # Agent outputs by iteration
    iteration_results: List[IterationResult] = Field(default_factory=list)

    # Current agent outputs
    current_researcher_output: Optional[str] = None
    current_critic_output: Optional[str] = None
    current_architect_output: Optional[str] = None
    current_estimator_output: Optional[str] = None

    # Consensus tracking
    consensus_score: float = 0.0
    consensus_reached: bool = False
    unresolved_conflicts: List[str] = Field(default_factory=list)
    key_agreements: List[str] = Field(default_factory=list)

    # Workflow status
    status: str = "initialized"  # initialized, planning, running, paused, completed, failed
    error: Optional[str] = None
    human_feedback: Optional[str] = None

    # Metadata
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def add_iteration_result(self, result: IterationResult):
        """Add a result from an iteration"""
        self.iteration_results.append(result)
        self.current_iteration = result.iteration

    def get_previous_outputs(self) -> Dict[str, str]:
        """Get outputs from all agents for context"""
        outputs = {}
        if self.current_researcher_output:
            outputs["Researcher"] = self.current_researcher_output
        if self.current_critic_output:
            outputs["Critic"] = self.current_critic_output
        if self.current_architect_output:
            outputs["Architect"] = self.current_architect_output
        if self.current_estimator_output:
            outputs["Estimator"] = self.current_estimator_output
        return outputs

    def get_current_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state"""
        return {
            "topic": self.topic,
            "iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "consensus_score": self.consensus_score,
            "consensus_reached": self.consensus_reached,
            "status": self.status,
        }

    def should_continue(self) -> bool:
        """Determine if research should continue"""
        # Stop if consensus reached
        if self.consensus_reached:
            return False

        # Stop if max iterations reached
        if self.current_iteration >= self.max_iterations:
            return False

        # Continue if below min iterations
        if self.current_iteration < self.min_iterations:
            return True

        # Continue if no consensus but can still iterate
        return True
