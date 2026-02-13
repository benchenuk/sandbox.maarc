"""
Consensus-CLI Package
Iterative Multi-Agent Research Engine
"""

__version__ = "0.1.0"
__author__ = "Consensus-CLI Team"

from consensus.workflow.graph import ResearchGraph
from consensus.agents.base import BaseAgent
from consensus.models.lite_llm_client import LiteLLMClient

__all__ = [
    "ResearchGraph",
    "BaseAgent",
    "LiteLLMClient",
]
