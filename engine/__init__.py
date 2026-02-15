"""
Consensus-CLI Package
Iterative Multi-Agent Research Engine
"""

__version__ = "0.4.0"
__author__ = "Consensus-CLI Team"

from engine.v2.graph import ResearchGraphV2
from engine.models.llm_client import LLMClient

__all__ = [
    "ResearchGraphV2",
    "LLMClient",
]
