"""
Consensus-CLI Package
Iterative Multi-Agent Research Engine
"""

__version__ = "0.1.0"
__author__ = "Consensus-CLI Team"

from consensus.workflow.graph import ResearchGraph
from consensus.agents.base import BaseAgent
from consensus.models.llm_client import LLMClient

__all__ = [
    "ResearchGraph",
    "BaseAgent",
    "LLMClient",
]
