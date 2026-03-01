#!/usr/bin/env python3
"""
Unit tests for V2 implementation - Design B.2: Draft Report Pattern

Tests the 5-phase iteration loop:
Research → Draft Report → Critique → Decision → Final
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from engine.v2.state import ResearchState, AgentConfig
from engine.v2.nodes import OrchestratorNode, AgentNode, SynthesisNode, TEAM_GENERATION_PROMPT


@pytest.fixture
def mock_config():
    """Mock config with new structure (Design B.2)"""
    return {
        "research": {
            "max_iterations": 3
        },
        "orchestrator": {
            "provider": "test_provider",
            "temperature": 0.7,
            "team_generation": {
                "min_agents": 2,
                "max_agents": 5,
                "require_skeptic": True
            }
        },
        "models": {
            "providers": {
                "test_provider": {
                    "enabled": True,
                    "api_base": "http://localhost:4000",
                    "api_key": "test_key",
                    "default_model": "gpt-4o"
                }
            }
        },
        "agents": {
            "default": {
                "provider": "test_provider",
                "temperature": 0.7
            }
        },
        "synthesizer": {
            "provider": "test_provider",
            "temperature": 0.3
        }
    }


@pytest.mark.asyncio
async def test_evaluate_consensus_increments_iteration(mock_config):
    """Test that evaluate_consensus properly increments current_iteration"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='{"decision": "IN_PROGRESS", "updated_draft": "# Draft"}')
    orchestrator = OrchestratorNode(mock_llm)
    
    # Test iteration 0 -> 1 with consensus reached
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=3
    )
    
    result = await orchestrator.evaluate_consensus(state)
    
    # Key assertions
    assert "current_iteration" in result, "evaluate_consensus must return current_iteration"
    assert result["current_iteration"] == 1, f"iteration should be 1, got {result['current_iteration']}"
    # With max_iterations=3, iteration 1 should continue (not finalize)
    assert result["consensus_status"] in ["REACHED", "IN_PROGRESS"]
    
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
    assert result2["current_iteration"] == 2, f"iteration should be 2, got {result2['current_iteration']}"
    
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
    
    result = await orchestrator.plan_team(state)
    
    # Verify team manifest is populated
    assert "team_manifest" in result
    team = result["team_manifest"]
    
    # Should have 4 agents from LLM response
    assert len(team) == 4
    
    roles = [a.role for a in team]
    assert "macroeconomist" in roles
    assert "demographer" in roles
    assert "policy-analyst" in roles
    assert "skeptic" in roles
    
    # Verify LLM was called with team generation prompt
    mock_llm.complete.assert_called_once()
    call_args = mock_llm.complete.call_args
    assert "Japanese economy challenges" in call_args.kwargs.get("prompt", "")
    
    print("\n✓ Orchestrator generates team dynamically via LLM")
    print(f"  Team: {', '.join(roles)}")


@pytest.mark.asyncio
async def test_orchestrator_enforces_max_agents(mock_config):
    """Test that orchestrator enforces max_agents limit from config"""
    mock_llm = MagicMock()
    
    # Mock LLM returning too many agents
    mock_response = json.dumps([
        {"role": f"Expert {i}", "domain": "Test", "goal": "Test goal"}
        for i in range(10)  # 10 agents, but max is 5
    ])
    mock_llm.complete = AsyncMock(return_value=mock_response)
    
    orchestrator = OrchestratorNode(mock_llm)
    state = ResearchState(topic="Test", config=mock_config)
    
    result = await orchestrator.plan_team(state)
    team = result["team_manifest"]
    
    # Should be truncated to max_agents (5), but Skeptic may be added after
    # So check that original LLM response was truncated
    assert len(team) <= 6, f"Team should be at most 6 (5 + skeptic), got {len(team)}"
    
    print(f"\n✓ Orchestrator enforces max_agents limit (truncated to {len(team)})")


@pytest.mark.asyncio
async def test_orchestrator_adds_required_skeptic(mock_config):
    """Test that orchestrator adds Skeptic when required and missing"""
    mock_llm = MagicMock()
    
    # Mock response without a Skeptic
    mock_response = json.dumps([
        {"role": "Economist", "domain": "Economics", "goal": "Analyze economy"}
    ])
    mock_llm.complete = AsyncMock(return_value=mock_response)
    
    orchestrator = OrchestratorNode(mock_llm)
    state = ResearchState(topic="Test", config=mock_config)
    
    result = await orchestrator.plan_team(state)
    team = result["team_manifest"]
    
    # Should have added Skeptic
    roles = [a.role for a in team]
    assert any("skeptic" in r.lower() for r in roles), "Skeptic should be added when required"
    
    print("\n✓ Orchestrator adds required Skeptic when missing")


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
    
    result = await orchestrator.plan_team(state)
    
    team = result["team_manifest"]
    # 2 agents from LLM + possibly Skeptic if required
    assert len(team) >= 2
    roles = [a.role for a in team]
    assert "technologist" in roles
    assert "ethicist" in roles
    
    print("\n✓ Orchestrator handles JSON in markdown code blocks")


@pytest.mark.asyncio
async def test_orchestrator_fallback_on_invalid_json(mock_config):
    """Test that orchestrator falls back to default team on invalid LLM response"""
    mock_llm = MagicMock()
    
    # Mock invalid JSON response
    mock_llm.complete = AsyncMock(return_value="This is not valid JSON {invalid}")
    
    orchestrator = OrchestratorNode(mock_llm)
    state = ResearchState(topic="Test topic", config=mock_config)
    
    result = await orchestrator.plan_team(state)
    
    # Should have fallback team
    team = result["team_manifest"]
    assert len(team) >= 2  # Fallback has at least 2 agents
    
    print("\n✓ Orchestrator falls back to default team on invalid JSON")


@pytest.mark.asyncio
async def test_orchestrator_draft_report(mock_config):
    """Test Design B.2: Orchestrator creates comprehensive draft report"""
    mock_llm = MagicMock()
    
    # Mock draft report response
    mock_draft = """# Draft Report: Climate Policy

## Executive Summary
Climate policies show promise but face implementation challenges.

## Key Findings
### Economic Impact
Mixed results across sectors...

## Critical Analysis
### Points of Agreement
All experts agree on urgency...

### Areas of Debate
Cost distribution remains contentious..."""
    
    mock_llm.complete = AsyncMock(return_value=mock_draft)
    
    orchestrator = OrchestratorNode(mock_llm)
    
    state = ResearchState(
        topic="Climate policy",
        config=mock_config,
        current_iteration=1,
        agent_outputs={
            "Climate Scientist": "Carbon analysis...",
            "Economist": "Economic analysis..."
        }
    )
    
    result = await orchestrator.draft_report(state)
    
    # Verify draft report is created
    assert "draft_report" in result
    assert "Executive Summary" in result["draft_report"]
    assert "Key Findings" in result["draft_report"]
    assert result["status"] == "critiquing"
    
    print("\n✓ Orchestrator creates comprehensive draft report (Design B.2)")


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
    """Test AgentConfig Pydantic model with provider field"""
    config = AgentConfig(
        role="Test Role",
        domain="Test Domain",
        goal="Test Goal",
        provider="test_provider",
        model="gpt-4o",
        temperature=0.7
    )
    
    assert config.role == "test-role"
    assert config.domain == "Test Domain"
    assert config.provider == "test_provider"
    assert config.temperature == 0.7
    
    print("\n✓ AgentConfig model works correctly (with provider)")


def test_state_draft_report_and_critiques():
    """Test Design B.2: State has draft_report and draft_critiques fields"""
    state = ResearchState(
        topic="Test topic",
        draft_report="Test draft...",
        draft_critiques={
            "Agent1": "Critique 1",
            "Agent2": "Critique 2"
        }
    )
    
    # Test draft_report field
    assert state.draft_report == "Test draft..."
    
    # Test draft_critiques field
    assert "Agent1" in state.draft_critiques
    assert state.draft_critiques["Agent1"] == "Critique 1"
    
    print("\n✓ State has draft_report and draft_critiques (Design B.2)")


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
    """Test agent node research method with provider"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Mocked analysis about climate policy...")
    
    config = AgentConfig(
        role="Climate Scientist",
        domain="Environmental Science",
        goal="Assess carbon impact",
        provider="test_provider",
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
    assert "climate-scientist" in result["agent_outputs"]
    
    # Verify LLM was called with correct parameters
    call_args = mock_llm.complete.call_args
    assert call_args.kwargs["system_prompt"] == "You are a Climate Scientist..."
    assert call_args.kwargs["provider"] == "test_provider"
    
    print("\n✓ Agent node research works with provider")


@pytest.mark.asyncio
async def test_agent_critique_draft(mock_config):
    """Test Design B.2: Agent critiques draft report"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="The draft understates economic risks...")
    
    config = AgentConfig(
        role="Economist",
        domain="Economics",
        goal="Analyze costs",
        provider="test_provider",
        system_prompt="You are an Economist...",
        temperature=0.7
    )
    
    agent = AgentNode(mock_llm, config)
    
    state = ResearchState(
        topic="Climate policy",
        config=mock_config,
        draft_report="# Draft Report\n\nClimate policies show promise..."
    )
    
    result = await agent.critique_draft(state)
    
    # Verify critique is stored in draft_critiques
    assert "draft_critiques" in result
    assert "economist" in result["draft_critiques"]
    
    # Verify LLM was called
    mock_llm.complete.assert_called_once()
    call_args = mock_llm.complete.call_args
    assert "Draft Report" in call_args.kwargs["prompt"]
    
    print("\n✓ Agent critiques draft report (Design B.2)")


@pytest.mark.asyncio
async def test_synthesis_uses_draft_and_critiques(mock_config):
    """Test Design B.2: Synthesizer uses draft_report and draft_critiques"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="# Final Report\n\nComprehensive analysis...")
    
    synthesizer = SynthesisNode(mock_llm)
    
    state = ResearchState(
        topic="Climate policy analysis",
        config=mock_config,
        agent_outputs={
            "Climate Scientist": "Carbon reduction potential is significant...",
            "Economist": "Economic impact varies by sector...",
        },
        draft_report="# Draft Report\n\nClimate policies show promise...",
        draft_critiques={
            "Climate Scientist": "Missing temperature data...",
            "Economist": "Understates costs..."
        },
        consensus_status="REACHED",
        current_iteration=2,
        team_manifest=[
            AgentConfig(role="Climate Scientist", domain="Science", goal="Assess impact", provider="test"),
            AgentConfig(role="Economist", domain="Economics", goal="Analyze costs", provider="test"),
        ]
    )
    
    result = await synthesizer.generate_report(state)
    
    assert result["status"] == "completed"
    assert "final_report" in result
    assert result["final_report"] == "# Final Report\n\nComprehensive analysis..."
    
    # Verify LLM was called with draft
    call_args = mock_llm.complete.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Draft Report" in prompt or "DRAFT REPORT" in prompt
    
    print("\n✓ Synthesizer uses draft")


def test_team_generation_prompt_structure():
    """Test that team generation prompt includes necessary instructions"""
    prompt = TEAM_GENERATION_PROMPT.format(topic="Test topic")
    
    assert "3-5 distinct expert roles" in prompt
    assert "Skeptic" in prompt or "Risk Analyst" in prompt
    assert "valid JSON array" in prompt
    assert "role" in prompt
    assert "domain" in prompt
    assert "goal" in prompt
    
    print("\n✓ Team generation prompt has correct structure")


if __name__ == "__main__":
    print("=" * 60)
    print("V2 Implementation Tests - Design B.2: Draft Report Pattern")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])
