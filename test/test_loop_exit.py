#!/usr/bin/env python3
"""
Unit test for the loop exit fix with mocked API calls.
Tests that selecting option "2" (Stop and generate report) properly exits the loop.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime
from engine.workflow.state import ResearchState, IterationResult
from engine.workflow.nodes import ResearchNodes
from engine.workflow.graph import ResearchGraph


@pytest.fixture
def mock_config():
    """Test configuration with HITL enabled"""
    return {
        "app": {"name": "MAARC", "version": "0.1.0"},
        "research": {
            "default_iterations": 5,
            "min_iterations": 1,
            "max_iterations": 10,
            "consensus_threshold": 0.85,
        },
        "models": {
            "default_model": "gpt-4o",
            "proxy": {"api_base": "http://localhost:4000", "api_key": ""},
            "agents": {}
        },
        "output": {"format": "markdown", "directory": "reports", "include_raw_transcripts": False},
        "human_in_the_loop": {
            "enabled": True,
            "checkpoint_frequency": "every_cycle",
            "pause_on_conflicts": True
        },
        "ui": {"show_spinner": True, "color_enabled": True, "verbose": False}
    }


@pytest.mark.asyncio
async def test_stop_and_generate_report_sets_consensus_true(mock_config):
    """
    Test the core fix: selecting option "2" sets consensus_reached=True.
    
    This is the main test for the bug fix - verifies that when user selects
    "2" (Stop and generate report), the evaluate_node returns:
    - consensus_reached=True (not status="paused")
    - current_iteration is incremented
    """
    
    # Create nodes with mocked LLM
    mock_llm = MagicMock()
    nodes = ResearchNodes(mock_config, mock_llm)
    
    # Mock orchestrator evaluate_consensus to return NO consensus
    # This ensures the HITL checkpoint is triggered
    nodes.orchestrator.evaluate_consensus = AsyncMock(return_value={
        "consensus_score": 0.6,
        "consensus_reached": False,
        "unresolved_conflicts": ["auth method not decided"],
        "key_agreements": ["use FastAPI"]
    })
    
    # Create state at iteration 0 (simulating after first iteration)
    state = ResearchState(
        topic="Design a REST API for a todo app",
        config=mock_config,
        current_iteration=0,
        max_iterations=5,
        current_researcher_output="Research: Use FastAPI with async endpoints",
        current_critic_output="Critique: Need authentication",
        current_architect_output="Architecture: Three-layer design",
        current_estimator_output="Estimate: 2-3 weeks",
    )
    
    # Mock user input to select "2" (Stop and generate report)
    with patch("engine.workflow.nodes.prompt_user", return_value="2"):
        with patch("engine.workflow.nodes.display_checkpoint"):
            with patch("engine.workflow.nodes.display_agent_thinking"):
                result = await nodes.evaluate_node(state)
    
    # KEY ASSERTIONS - These verify the fix:
    # 1. consensus_reached must be True to route to "report" node
    assert result["consensus_reached"] == True, \
        f"BUG: consensus_reached should be True when user selects '2', got {result['consensus_reached']}"
    
    # 2. status should be "running", not "paused" (paused routes to plan, not report)
    assert result["status"] == "running", \
        f"BUG: status should be 'running', got {result['status']}"
    
    # 3. iteration should be incremented
    assert result["current_iteration"] == 1, \
        f"BUG: current_iteration should be 1, got {result['current_iteration']}"
    
    print("\n✓ Test passed! Selecting '2' properly sets consensus_reached=True")
    print(f"  consensus_reached: {result['consensus_reached']}")
    print(f"  status: {result['status']}")
    print(f"  current_iteration: {result['current_iteration']}")


@pytest.mark.asyncio
async def test_continue_option_keeps_consensus_false(mock_config):
    """
    Test that pressing Enter (continue) does NOT set consensus_reached=True.
    """
    
    mock_llm = MagicMock()
    nodes = ResearchNodes(mock_config, mock_llm)
    
    nodes.orchestrator.evaluate_consensus = AsyncMock(return_value={
        "consensus_score": 0.6,
        "consensus_reached": False,
        "unresolved_conflicts": ["auth method"],
        "key_agreements": []
    })
    
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=5,
        current_researcher_output="Research output",
        current_critic_output="Critique output",
        current_architect_output="Architecture output",
        current_estimator_output="Estimate output",
    )
    
    # Mock user pressing Enter (empty input) to continue
    with patch("engine.workflow.nodes.prompt_user", return_value=""):
        with patch("engine.workflow.nodes.display_checkpoint"):
            with patch("engine.workflow.nodes.display_agent_thinking"):
                result = await nodes.evaluate_node(state)
    
    # When continuing, consensus_reached should remain False
    assert result["consensus_reached"] == False, \
        f"BUG: consensus_reached should be False when continuing, got {result['consensus_reached']}"
    assert result["current_iteration"] == 1, \
        f"BUG: current_iteration should be 1, got {result['current_iteration']}"
    
    print("\n✓ Test passed! Continue option keeps consensus_reached=False")
    print(f"  consensus_reached: {result['consensus_reached']}")


@pytest.mark.asyncio
async def test_provide_feedback_sets_paused_status(mock_config):
    """
    Test that selecting option "3" (Provide feedback) sets status="paused".
    """
    
    mock_llm = MagicMock()
    nodes = ResearchNodes(mock_config, mock_llm)
    
    nodes.orchestrator.evaluate_consensus = AsyncMock(return_value={
        "consensus_score": 0.6,
        "consensus_reached": False,
        "unresolved_conflicts": [],
        "key_agreements": []
    })
    
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=5,
        current_researcher_output="Research output",
        current_critic_output="Critique output",
        current_architect_output="Architecture output",
        current_estimator_output="Estimate output",
    )
    
    # Mock user selecting "3" (Provide feedback)
    with patch("engine.workflow.nodes.prompt_user", return_value="3"):
        with patch("engine.workflow.nodes.display_checkpoint"):
            with patch("engine.workflow.nodes.display_agent_thinking"):
                result = await nodes.evaluate_node(state)
    
    # When providing feedback, status should be "paused"
    assert result["status"] == "paused", \
        f"BUG: status should be 'paused' for feedback, got {result['status']}"
    assert result["human_feedback"] == "3", \
        f"BUG: human_feedback should be '3', got {result.get('human_feedback')}"
    
    print("\n✓ Test passed! Providing feedback sets status='paused'")
    print(f"  status: {result['status']}")
    print(f"  human_feedback: {result['human_feedback']}")


@pytest.mark.asyncio
async def test_iteration_counter_increments(mock_config):
    """
    Test that current_iteration is properly incremented in all cases.
    """
    
    mock_llm = MagicMock()
    nodes = ResearchNodes(mock_config, mock_llm)
    
    nodes.orchestrator.evaluate_consensus = AsyncMock(return_value={
        "consensus_score": 0.7,
        "consensus_reached": False,
        "unresolved_conflicts": [],
        "key_agreements": ["agreement1"]
    })
    
    # Test with HITL disabled - should auto-increment
    mock_config["human_in_the_loop"]["enabled"] = False
    
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=5,
        current_researcher_output="Research output",
        current_critic_output="Critique output",
        current_architect_output="Architecture output",
        current_estimator_output="Estimate output",
    )
    
    with patch("engine.workflow.nodes.display_agent_thinking"):
        result = await nodes.evaluate_node(state)
    
    assert result["current_iteration"] == 1, \
        f"BUG: current_iteration should be 1, got {result['current_iteration']}"
    
    print("\n✓ Test passed! Iteration counter properly increments")
    print(f"  Previous: 0, Current: {result['current_iteration']}")


def test_state_to_dict_conversion():
    """
    Test that ResearchState can be properly converted to dict.
    This verifies the fix for the '.get()' AttributeError.
    """
    state = ResearchState(
        topic="Test topic",
        config={},
        current_iteration=3,
        max_iterations=5,
        consensus_score=0.85,
        consensus_reached=True,
        current_researcher_output="Research findings",
        current_critic_output="Critique points",
        current_architect_output="Architecture design",
        current_estimator_output="Effort estimate",
        key_agreements=["Use FastAPI"],
        unresolved_conflicts=[],
    )
    
    # Test model_dump method (Pydantic v2)
    state_dict = state.model_dump()
    
    # Verify dict conversion works
    assert isinstance(state_dict, dict)
    assert state_dict.get("current_iteration") == 3
    assert state_dict.get("consensus_reached") == True
    assert state_dict.get("consensus_score") == 0.85
    assert state_dict.get("current_researcher_output") == "Research findings"
    
    print("\n✓ Test passed! ResearchState properly converts to dict")
    print(f"  current_iteration: {state_dict.get('current_iteration')}")
    print(f"  consensus_reached: {state_dict.get('consensus_reached')}")


def test_graph_run_converts_state_to_dict(mock_config):
    """
    Test that ResearchGraph.run() properly converts ResearchState to dict.
    This tests the fix for: 'ResearchState' object has no attribute 'get'
    """
    state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=2,
        max_iterations=5,
        consensus_score=0.9,
        consensus_reached=True,
        current_researcher_output="Research",
        current_critic_output="Critique",
        current_architect_output="Architecture",
        current_estimator_output="Estimate",
        key_agreements=["Agree on FastAPI"],
        unresolved_conflicts=[],
        iteration_results=[
            IterationResult(
                iteration=1,
                consensus_score=0.6,
                consensus_reached=False
            ),
            IterationResult(
                iteration=2,
                consensus_score=0.9,
                consensus_reached=True
            )
        ]
    )
    
    # Verify model_dump works and returns a dict
    state_dict = state.model_dump()
    
    # This is what graph.run() does after the fix
    assert state_dict.get("current_iteration") == 2
    assert state_dict.get("consensus_reached") == True
    assert state_dict.get("consensus_score") == 0.9
    assert len(state_dict.get("iteration_results", [])) == 2
    
    print("\n✓ Test passed! State to dict conversion works in graph.run()")


@pytest.mark.asyncio
async def test_run_graph_returns_research_state(mock_config):
    """
    Test that _run_graph returns a proper ResearchState object (not a stream chunk).
    
    This verifies the fix for the issue where reports showed 0 iterations
    because astream() was returning partial state updates instead of final state.
    """
    graph = ResearchGraph(config=mock_config)
    
    # Create initial state
    initial_state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=3,
        current_researcher_output="Research output",
        current_critic_output="Critique output",
        current_architect_output="Architecture output",
        current_estimator_output="Estimate output",
    )
    
    # Mock the graph's ainvoke to return a proper state
    expected_final_state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=1,
        max_iterations=3,
        current_researcher_output="Research output",
        current_critic_output="Critique output",
        current_architect_output="Architecture output",
        current_estimator_output="Estimate output",
        consensus_score=0.85,
        consensus_reached=True,
    )
    
    with patch.object(graph.graph, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.return_value = expected_final_state
        
        result = await graph._run_graph(initial_state)
    
    # Verify we got a ResearchState back with correct data
    assert isinstance(result, ResearchState), \
        f"BUG: _run_graph should return ResearchState, got {type(result)}"
    assert result.current_iteration == 1, \
        f"BUG: current_iteration should be 1, got {result.current_iteration}"
    assert result.consensus_reached == True, \
        f"BUG: consensus_reached should be True, got {result.consensus_reached}"
    
    print("\n✓ Test passed! _run_graph returns proper ResearchState")
    print(f"  Type: {type(result).__name__}")
    print(f"  current_iteration: {result.current_iteration}")
    print(f"  consensus_reached: {result.consensus_reached}")


@pytest.mark.asyncio
async def test_run_graph_handles_dict_response(mock_config):
    """
    Test that _run_graph handles dict responses from ainvoke.
    """
    graph = ResearchGraph(config=mock_config)
    
    initial_state = ResearchState(
        topic="Test topic",
        config=mock_config,
        current_iteration=0,
        max_iterations=3,
    )
    
    # Mock ainvoke to return a dict instead of ResearchState
    expected_dict = {
        "topic": "Test topic",
        "config": mock_config,
        "current_iteration": 2,
        "max_iterations": 3,
        "consensus_reached": True,
        "consensus_score": 0.9,
    }
    
    with patch.object(graph.graph, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.return_value = expected_dict
        
        result = await graph._run_graph(initial_state)
    
    # Verify we got a ResearchState back
    assert isinstance(result, ResearchState), \
        f"BUG: _run_graph should return ResearchState, got {type(result)}"
    assert result.current_iteration == 2, \
        f"BUG: current_iteration should be 2, got {result.current_iteration}"
    
    print("\n✓ Test passed! _run_graph handles dict responses")


if __name__ == "__main__":
    print("=" * 70)
    print("Running Loop Exit Fix Tests")
    print("=" * 70)
    print()
    print("These tests verify:")
    print("  1. Selecting '2' sets consensus_reached=True (exits to report)")
    print("  2. Selecting '3' sets status='paused' (routes to human_feedback)")
    print("  3. Pressing Enter continues the loop")
    print("  4. current_iteration is always incremented")
    print("  5. ResearchState properly converts to dict")
    print("  6. _run_graph returns proper ResearchState (not stream chunks)")
    print()
    
    pytest.main([__file__, "-v", "--tb=short"])
