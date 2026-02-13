"""
Consensus-CLI Package
Iterative Multi-Agent Research Engine
"""

__version__ = "0.2.0"
__author__ = "Consensus-CLI Team"

from consensus.v2.graph import ResearchGraphV2
from consensus.models.llm_client import LLMClient

__all__ = [
    "ResearchGraphV2",
    "LLMClient",
]
