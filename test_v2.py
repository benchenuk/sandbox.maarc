#!/usr/bin/env python3
"""
Unit tests for V2 implementation - Iteration 2: Dynamic Strategy
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from consensus.v2.state import ResearchState, AgentConfig
from consensus.v2.nodes import OrchestratorNode, AgentNode, SynthesisNode, TEAM_GENERATION_PROMPT


@pytest.fixture
def mock_config():
    return {
        "models": {
            "proxy": {"api_base": "http://localhost:4000", "api_key": ""},
            "default_model": "gpt-4o"
        }
    }


@pytest.mark.asyncio
async def test_evaluate_consensus_increments_iteration(mock_config):
    """Test that evaluate_consensus properly increments current_iteration"""
    mock_llm = MagicMock()
    orchestrator = OrchestratorNode(mock_llm)
    
    # Test iteration 0 -> 1 with consensus reached
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=3
    )
    
    result = await orchestrator.evaluate_consensus(state)
    
    # Key assertions - this was the bug!
    assert "current_iteration" in result, "BUG: evaluate_consensus must return current_iteration"
    assert result["current_iteration"] == 1, f"BUG: iteration should be 1, got {result['current_iteration']}"
    assert result["consensus_status"] == "REACHED"
    
    print("\n✓ evaluate_consensus increments iteration correctly")
    print(f"  Previous: 0, Current: {result['current_iteration']}")
    
    # Test iteration continues properly
    state2 = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=1,
        max_iterations=3
    )
    
    result2 = await orchestrator.evaluate_consensus(state2)
    assert result2["current_iteration"] == 2, f"BUG: iteration should be 2, got {result2['current_iteration']}"
    
    print(f"  Previous: 1, Current: {result2['current_iteration']}")


@pytest.mark.asyncio
async def test_orchestrator_generates_team_dynamically(mock_config):
    """Test that orchestrator generates team via LLM based on topic"""
    mock_llm = MagicMock()
    
    # Mock LLM response with valid JSON
    mock_response = json.dumps([
        {"role": "Macroeconomist", "domain": "Economics", "goal": "Analyze GDP and inflation trends"},
        {"role": "Demographer", "domain": "Demographics", "goal": "Study population aging patterns"},
        {"role": "Policy Analyst", "domain": "Public Policy", "goal": "Evaluate government responses"},
        {"role": "Skeptic", "domain": "Critical Analysis", "goal": "Challenge optimistic assumptions"}
    ])
    mock_llm.complete = AsyncMock(return_value=mock_response)
    
    orchestrator = OrchestratorNode(mock_llm)
    
    state = ResearchState(topic="Japanese economy challenges", config=mock_config)
    
    result = await orchestrator.propose_team(state)
    
    # Verify team manifest is populated
    assert "team_manifest" in result
    team = result["team_manifest"]
    
    # Should have 4 agents from LLM response
    assert len(team) == 4
    
    roles = [a.role for a in team]
    assert "Macroeconomist" in roles
    assert "Demographer" in roles
    assert "Policy Analyst" in roles
    assert "Skeptic" in roles
    
    # Verify LLM was called with team generation prompt
    mock_llm.complete.assert_called_once()
    call_args = mock_llm.complete.call_args
    assert "Japanese economy challenges" in call_args.kwargs.get("prompt", "")
    
    print("\n✓ Orchestrator generates team dynamically via LLM")
    print(f"  Team: {', '.join(roles)}")


@pytest.mark.asyncio
async def test_orchestrator_handles_json_in_markdown(mock_config):
    """Test that orchestrator handles JSON wrapped in markdown code blocks"""
    mock_llm = MagicMock()
    
    # Mock LLM response with JSON in markdown block
    mock_response = """Here's the team configuration:

```json
[
  {"role": "Technologist", "domain": "Technology", "goal": "Assess technical feasibility"},
  {"role": "Ethicist", "domain": "Ethics", "goal": "Evaluate moral implications"}
]
```

This team should provide comprehensive analysis."""
    
    mock_llm.complete = AsyncMock(return_value=mock_response)
    
    orchestrator = OrchestratorNode(mock_llm)
    state = ResearchState(topic="AI regulation", config=mock_config)
    
    result = await orchestrator.propose_team(state)
    
    team = result["team_manifest"]
    assert len(team) == 2
    assert team[0].role == "Technologist"
    assert team[1].role == "Ethicist"
    
    print("\n✓ Orchestrator handles JSON in markdown code blocks")


@pytest.mark.asyncio
async def test_orchestrator_fallback_on_invalid_json(mock_config):
    """Test that orchestrator falls back to default team on invalid LLM response"""
    mock_llm = MagicMock()
    
    # Mock invalid JSON response
    mock_llm.complete = AsyncMock(return_value="This is not valid JSON {invalid}")
    
    orchestrator = OrchestratorNode(mock_llm)
    state = ResearchState(topic="Test topic", config=mock_config)
    
    result = await orchestrator.propose_team(state)
    
    # Should have fallback team
    team = result["team_manifest"]
    assert len(team) == 2  # Fallback has 2 agents
    
    roles = [a.role for a in team]
    assert "Domain Expert" in roles
    assert "Skeptic" in roles
    
    print("\n✓ Orchestrator falls back to default team on invalid JSON")


def test_system_prompt_generation():
    """Test that orchestrator generates appropriate system prompts for roles"""
    mock_llm = MagicMock()
    orchestrator = OrchestratorNode(mock_llm)
    
    prompt = orchestrator._generate_system_prompt(
        role="Climate Scientist",
        domain="Environmental Science",
        goal="Assess carbon impact of policies"
    )
    
    assert "Climate Scientist" in prompt
    assert "Environmental Science" in prompt
    assert "Assess carbon impact of policies" in prompt
    assert "Focus STRICTLY" in prompt  # Guideline included
    
    print("\n✓ System prompt generation works correctly")


def test_agent_config_model():
    """Test AgentConfig Pydantic model"""
    config = AgentConfig(
        role="Test Role",
        domain="Test Domain",
        goal="Test Goal",
        model="gpt-4o",
        temperature=0.7
    )
    
    assert config.role == "Test Role"
    assert config.domain == "Test Domain"
    assert config.temperature == 0.7
    
    print("\n✓ AgentConfig model works correctly")


def test_state_agent_outputs_dict():
    """Test that state uses flexible agent_outputs dict"""
    state = ResearchState(
        topic="Test topic",
        agent_outputs={}
    )
    
    # Test setting and getting outputs with dynamic roles
    state.set_agent_output("Macroeconomist", "GDP analysis...")
    state.set_agent_output("Demographer", "Population trends...")
    state.set_agent_output("Custom Expert", "Custom analysis...")
    
    assert "Macroeconomist" in state.agent_outputs
    assert "Demographer" in state.agent_outputs
    assert "Custom Expert" in state.agent_outputs
    
    print("\n✓ State agent_outputs dict handles dynamic roles")


def test_state_debate_history():
    """Test debate history tracking"""
    state = ResearchState(topic="Test")
    
    state.add_debate_entry(
        from_role="Skeptic",
        to_role="Macroeconomist",
        message="Your GDP projections assume steady growth, but recessions?",
        entry_type="critique"
    )
    
    assert len(state.debate_history) == 1
    entry = state.debate_history[0]
    assert entry["from"] == "Skeptic"
    assert entry["to"] == "Macroeconomist"
    
    print("\n✓ Debate history tracking works correctly")


@pytest.mark.asyncio
async def test_agent_node_research(mock_config):
    """Test agent node research method with dynamic role"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Mocked analysis about climate policy...")
    
    config = AgentConfig(
        role="Climate Scientist",
        domain="Environmental Science",
        goal="Assess carbon impact",
        system_prompt="You are a Climate Scientist...",
        temperature=0.5
    )
    
    agent = AgentNode(mock_llm, config)
    
    state = ResearchState(
        topic="Carbon tax effectiveness",
        config=mock_config
    )
    
    result = await agent.research(state)
    
    # Verify output is stored with dynamic role name
    assert "agent_outputs" in result
    assert "Climate Scientist" in result["agent_outputs"]
    
    # Verify LLM was called with correct system prompt
    call_args = mock_llm.complete.call_args
    assert call_args.kwargs["system_prompt"] == "You are a Climate Scientist..."
    
    print("\n✓ Agent node research works with dynamic role")


@pytest.mark.asyncio
async def test_synthesis_generates_report(mock_config):
    """Test synthesis node generates markdown report"""
    mock_llm = MagicMock()
    synthesizer = SynthesisNode(mock_llm)
    
    state = ResearchState(
        topic="Climate policy analysis",
        config=mock_config,
        agent_outputs={
            "Climate Scientist": "Carbon reduction potential is significant...",
            "Economist": "Economic impact varies by sector...",
        },
        consensus_status="REACHED",
        team_manifest=[
            AgentConfig(role="Climate Scientist", domain="Science", goal="Assess impact"),
            AgentConfig(role="Economist", domain="Economics", goal="Analyze costs"),
        ]
    )
    
    result = await synthesizer.generate_report(state)
    
    assert result["status"] == "completed"
    assert "end_time" in result
    
    print("\n✓ Synthesis generates report correctly")


def test_team_generation_prompt_structure():
    """Test that team generation prompt includes necessary instructions"""
    prompt = TEAM_GENERATION_PROMPT.format(topic="Test topic")
    
    assert "Project Manager" in prompt
    assert "3-5 distinct expert roles" in prompt
    assert "Skeptic" in prompt or "Risk Analyst" in prompt
    assert "valid JSON array" in prompt
    assert "role" in prompt
    assert "domain" in prompt
    assert "goal" in prompt
    
    print("\n✓ Team generation prompt has correct structure")


if __name__ == "__main__":
    print("=" * 60)
    print("V2 Implementation Tests - Iteration 2: Dynamic Strategy")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])
