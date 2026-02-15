"""
Consensus-CLI V2: Dynamic Multi-Agent Research Engine

Iteration 1: The "Dumb" Loop
- Domain-specific hardcoded agents
- Flexible agent_outputs dict state
- interrupt_before HITL checkpoint
"""

from engine.v2.state import ResearchState, AgentConfig
from engine.v2.graph import ResearchGraphV2

__all__ = ["ResearchState", "AgentConfig", "ResearchGraphV2"]
