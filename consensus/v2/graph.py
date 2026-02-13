"""
V2 Graph Definition - Iteration 2
LangGraph implementation with dynamic team generation
"""

import asyncio
from typing import Any, Dict, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from consensus.v2.state import ResearchState, AgentConfig
from consensus.v2.nodes import OrchestratorNode, AgentNode, SynthesisNode
from consensus.models.llm_client import LLMClient


class ResearchGraphV2:
    """
    V2 Research Graph - Iteration 2: Dynamic Strategy
    Features:
    - Orchestrator generates team dynamically via LLM
    - Flexible agent_outputs dict state
    - interrupt_before for HITL team approval
    - Sequential execution through dynamic agents
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_client = LLMClient(config)
        
        # Initialize nodes
        self.orchestrator = OrchestratorNode(self.llm_client)
        self.synthesizer = SynthesisNode(self.llm_client)
    
    def _build_graph(self, team_manifest: List[AgentConfig]) -> StateGraph:
        """
        Build the LangGraph state machine dynamically based on team manifest.
        
        Iteration 2: Build graph dynamically after team is approved.
        """
        workflow = StateGraph(ResearchState)
        
        # Add orchestrator node (team proposal happens before graph runs)
        workflow.add_node("evaluate", self._evaluate_wrapper)
        workflow.add_node("synthesize", self._synthesize_wrapper)
        
        # Add agent nodes dynamically based on team manifest
        agent_node_names = []
        for i, agent_config in enumerate(team_manifest):
            node_name = f"agent_{i}_{agent_config.role.lower().replace(' ', '_')}"
            agent_node_names.append(node_name)
            
            # Create wrapper that captures the agent config
            workflow.add_node(
                node_name, 
                self._make_agent_wrapper(agent_config)
            )
        
        # Set entry point to first agent
        if agent_node_names:
            workflow.set_entry_point(agent_node_names[0])
            
            # Chain agents sequentially
            for i in range(len(agent_node_names) - 1):
                workflow.add_edge(agent_node_names[i], agent_node_names[i + 1])
            
            # Last agent goes to evaluation
            workflow.add_edge(agent_node_names[-1], "evaluate")
        else:
            # No agents, go straight to evaluate
            workflow.set_entry_point("evaluate")
        
        # Conditional edge from evaluate
        workflow.add_conditional_edges(
            "evaluate",
            self._should_continue,
            {
                "continue": agent_node_names[0] if agent_node_names else "evaluate",  # Loop back
                "synthesize": "synthesize",
            }
        )
        
        workflow.add_edge("synthesize", END)
        
        # Compile with checkpointing
        checkpointer = MemorySaver()
        
        return workflow.compile(checkpointer=checkpointer)
    
    def _make_agent_wrapper(self, agent_config: AgentConfig):
        """Create a node function for a specific agent config."""
        async def agent_wrapper(state: ResearchState) -> Dict[str, Any]:
            agent = AgentNode(self.llm_client, agent_config)
            return await agent.research(state)
        
        return agent_wrapper
    
    async def _evaluate_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for consensus evaluation"""
        return await self.orchestrator.evaluate_consensus(state)
    
    async def _synthesize_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Wrapper for report synthesis"""
        return await self.synthesizer.generate_report(state)
    
    def _should_continue(self, state: ResearchState) -> str:
        """Determine if research should continue or synthesize"""
        if state.consensus_status == "REACHED":
            return "synthesize"
        if state.current_iteration >= state.max_iterations:
            return "synthesize"
        return "continue"
    
    def run(self, topic: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Run the research workflow with dynamic team generation.
        """
        # Initialize state
        initial_state = ResearchState(
            topic=topic,
            config=self.config,
            max_iterations=self.config.get("research", {}).get("default_iterations", 3),
            min_iterations=1,
            status="initialized",
            start_time=datetime.now().isoformat(),
        )
        
        try:
            print(f"\n{'='*60}")
            print("Starting V2 Research Workflow - Iteration 2")
            print(f"{'='*60}")
            print(f"Topic: {topic}")
            print("\n[Phase 1] Dynamic Team Generation")
            
            # Phase 1: Generate team dynamically
            team_result = asyncio.run(
                self.orchestrator.propose_team(initial_state)
            )
            
            # Update state with generated team
            team_manifest = team_result["team_manifest"]
            initial_state.team_manifest = team_manifest
            
            print(f"\n[Orchestrator] Proposed {len(team_manifest)} agents:")
            for i, agent in enumerate(team_manifest, 1):
                print(f"  {i}. {agent.role} ({agent.domain})")
            
            # Phase 2: HITL - Get user approval
            print(f"\n{'='*60}")
            print("HUMAN INTERVENTION REQUIRED")
            print(f"{'='*60}")
            print("\nApprove this team? (y/n/add <role>): ")
            
            from rich.console import Console
            console = Console()
            
            response = console.input(
                "\n[bold]Your choice:[/bold] "
            ).strip().lower()
            
            if response.startswith("add "):
                new_role = response[4:].strip()
                team_manifest.append(AgentConfig(
                    role=new_role,
                    domain="Custom",
                    goal=f"Provide {new_role} perspective",
                    system_prompt=self.orchestrator._generate_system_prompt(
                        new_role, "Custom", f"Provide {new_role} perspective"
                    )
                ))
                print(f"[+] Added {new_role} to team")
            elif response not in ("y", "yes"):
                print("[!] Using proposed team anyway")
            
            initial_state.team_approved = True
            initial_state.team_manifest = team_manifest
            
            # Phase 3: Build and run graph with dynamic team
            print(f"\n{'='*60}")
            print("[Phase 3] Agent Execution")
            print(f"{'='*60}")
            
            self.graph = self._build_graph(team_manifest)
            
            run_config = {
                "configurable": {
                    "thread_id": f"research_{topic[:20]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }
            }
            
            result = asyncio.run(self._run_graph(initial_state, run_config))
            
            # Generate and save report
            report_path = self._save_report(topic, result)
            
            return {
                "status": "completed",
                "topic": topic,
                "iterations": result.current_iteration,
                "consensus_status": result.consensus_status,
                "agent_outputs": result.agent_outputs,
                "team_manifest": [{"role": a.role, "domain": a.domain} for a in result.team_manifest],
                "report_path": report_path,
            }
            
        except Exception as e:
            print(f"\n[Error] Research failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
            }
    
    async def _run_graph(self, initial_state: ResearchState, run_config: Dict) -> ResearchState:
        """Run the compiled graph."""
        result = await self.graph.ainvoke(initial_state, run_config)
        
        # Convert dict back to ResearchState if needed
        if isinstance(result, dict):
            return ResearchState(**result)
        return result
    
    def _save_report(self, topic: str, state: ResearchState) -> str:
        """Generate and save markdown report to file."""
        import os
        import re
        from pathlib import Path
        
        # Generate filename
        safe_topic = re.sub(r'[^\w\s-]', '', topic)
        safe_topic = re.sub(r'[-\s]+', '-', safe_topic).lower()[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"v2_report_{safe_topic}_{timestamp}.md"
        
        # Get output directory from config
        output_dir = self.config.get("output", {}).get("directory", "reports")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filepath = output_path / filename
        
        # Build report content
        lines = [
            f"# Research Report: {topic}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Iterations:** {state.current_iteration}",
            f"**Consensus Status:** {state.consensus_status}",
            "",
            "## Team",
            "",
        ]
        
        for agent in state.team_manifest:
            lines.append(f"- **{agent.role}** ({agent.domain}): {agent.goal}")
        
        lines.extend(["", "## Expert Perspectives", ""])
        
        # Add each agent's output
        for role, output in state.agent_outputs.items():
            if "_critique_" not in role:
                lines.append(f"### {role}")
                lines.append("")
                lines.append(output)
                lines.append("")
        
        # Add critiques section
        critiques = {k: v for k, v in state.agent_outputs.items() if "_critique_" in k}
        if critiques:
            lines.extend(["## Critical Analysis", ""])
            for role, output in critiques.items():
                parts = role.replace("_critique_of_", " → ").replace("_", " ")
                lines.append(f"### {parts}")
                lines.append("")
                lines.append(output)
                lines.append("")
        
        # Write to file
        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"\n[Report] Saved to: {filepath}")
        return str(filepath)
