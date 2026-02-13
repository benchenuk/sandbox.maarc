"""
Agent Module
Contains all agent implementations
"""

from consensus.agents.base import BaseAgent
from consensus.agents.orchestrator import OrchestratorAgent
from consensus.agents.researcher import ResearcherAgent
from consensus.agents.critic import CriticAgent
from consensus.agents.architect import ArchitectAgent
from consensus.agents.estimator import EstimatorAgent

# Agent role definitions
AGENT_ROLES = {
    "orchestrator": "Coordinates the research workflow and evaluates consensus",
    "researcher": "Gathers information and documents findings",
    "critic": "Challenges assumptions and identifies flaws",
    "architect": "Synthesizes findings into coherent designs",
    "estimator": "Analyzes complexity and estimates efforts",
}

__all__ = [
    "BaseAgent",
    "OrchestratorAgent",
    "ResearcherAgent",
    "CriticAgent",
    "ArchitectAgent",
    "EstimatorAgent",
    "AGENT_ROLES",
]
