"""
V2 Graph Definition - Iteration 3: Parallel Execution with 4-Phase Loop
LangGraph implementation with hybrid parallel-sequential pattern

Design B.1: Research → Synthesis → Critique → Decision
"""

import asyncio
from typing import Any, Dict, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from consensus.v2.state import ResearchState, AgentConfig
from consensus.v2.nodes import OrchestratorNode, AgentNode, SynthesisNode
from consensus.models.llm_client import LLMClient
from rich.console import Console

console = Console()


class ResearchGraphV2:
    """
    V2 Research Graph - Design B.2: Draft Report Pattern
    
    Phase 1: RESEARCH (Fan-Out) - All agents produce detailed research
    Phase 2: DRAFT REPORT (Orchestrator) - Create comprehensive structured draft
    Phase 3: CRITIQUE (Fan-Out) - All agents critique the draft report
    Phase 4: DECISION (Orchestrator) - Evaluate quality, loop or finalize
    Phase 5: FINAL REPORT (Synthesizer) - Polish to professional deliverable
    
    Design from planning/DESIGN_B_2.md
    """
    
    # Toggle for including development appendices in reports
    # Set to False for production (clean reports only)
    # Set to True for development (includes draft, critiques, raw outputs)
    INCLUDE_DEV_APPENDICES: bool = True
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_client = LLMClient(config)
        
        # Initialize nodes
        self.orchestrator = OrchestratorNode(self.llm_client)
        self.synthesizer = SynthesisNode(self.llm_client)
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state machine with 4-phase iteration loop.
        """
        workflow = StateGraph(ResearchState)
        
        # Phase nodes
        workflow.add_node("orchestrate", self._orchestrate_entry)
        workflow.add_node("research_parallel", self._research_parallel)
        workflow.add_node("create_draft", self._draft_report_phase)
        workflow.add_node("critique_parallel", self._critique_parallel)
        workflow.add_node("evaluate", self._evaluate_phase)
        workflow.add_node("final_synthesize", self._synthesize_wrapper)
        
        # Entry
        workflow.set_entry_point("orchestrate")
        
        # Phase 1: Orchestrator entry → Research (fan-out)
        workflow.add_edge("orchestrate", "research_parallel")
        
        # Phase 2: Research → Draft Report (orchestrator, sequential)
        workflow.add_edge("research_parallel", "create_draft")
        
        # Phase 3: Draft → Critique (fan-out)
        workflow.add_edge("create_draft", "critique_parallel")
        
        # Phase 4: Critique → Evaluate (orchestrator decision)
        workflow.add_edge("critique_parallel", "evaluate")
        
        # Decision: Loop or Finalize
        workflow.add_conditional_edges(
            "evaluate",
            self._decision_router,
            {
                "loop": "orchestrate",      # New iteration, potentially new team
                "finalize": "final_synthesize",
            }
        )
        
        # Final
        workflow.add_edge("final_synthesize", END)
        
        # Compile with checkpointing
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)
    
    async def _orchestrate_entry(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase entry: Prepare for this iteration.
        First iteration: Initialize
        Subsequent iterations: Potentially reassemble team
        """
        if state.current_iteration == 0:
            console.print(f"\n[[cyan]Orchestrator[/cyan]]: Starting iteration 1")
            return {"current_iteration": 1, "status": "researching"}
        
        # Future: Dynamic team reassembly here
        console.print(f"\n[[cyan]Orchestrator[/cyan]]: Starting iteration {state.current_iteration}")
        return {"status": "researching"}
    
    async def _research_parallel(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 1: RESEARCH - All agents research in parallel (fan-out).
        """
        console.print(f"\n{'='*60}")
        console.print("Phase 1: RESEARCH (Parallel)")
        console.print(f"{'='*60}")
        
        tasks = []
        for agent_config in state.team_manifest:
            task = self._run_agent_research(state, agent_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_outputs = {}
        for agent_config, result in zip(state.team_manifest, results):
            if isinstance(result, Exception):
                console.print(f"[[cyan]{agent_config.role}[/cyan]]: [red]Error: {result}[/red]")
                all_outputs[agent_config.role] = f"Error: {result}"
            else:
                all_outputs.update(result)
        
        console.print(f"\n[[cyan]Orchestrator[/cyan]]: Collected {len(all_outputs)} research outputs")
        return {"agent_outputs": all_outputs, "status": "synthesizing"}
    
    async def _run_agent_research(self, state: ResearchState, agent_config: AgentConfig) -> Dict[str, str]:
        """Run a single agent's research."""
        agent = AgentNode(self.llm_client, agent_config)
        result = await agent.research(state)
        return result.get("agent_outputs", {})
    
    async def _draft_report_phase(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 2: DRAFT REPORT - Orchestrator creates comprehensive draft.
        """
        console.print(f"\n{'='*60}")
        console.print("Phase 2: DRAFT REPORT (Orchestrator)")
        console.print(f"{'='*60}")
        
        result = await self.orchestrator.draft_report(state)
        return result
    
    async def _critique_parallel(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 3: CRITIQUE - All agents critique the draft report (fan-out).
        """
        console.print(f"\n{'='*60}")
        console.print("Phase 3: CRITIQUE (Parallel)")
        console.print(f"{'='*60}")
        
        tasks = []
        for agent_config in state.team_manifest:
            task = self._run_agent_critique(state, agent_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_critiques = {}
        for agent_config, result in zip(state.team_manifest, results):
            if isinstance(result, Exception):
                console.print(f"[[cyan]{agent_config.role}[/cyan]]: [red]Error: {result}[/red]")
            else:
                all_critiques.update(result)
        
        console.print(f"\n[[cyan]Orchestrator[/cyan]]: Collected {len(all_critiques)} critiques of draft")
        
        # Store critiques separately (don't pollute agent_outputs)
        return {"draft_critiques": all_critiques, "status": "evaluating"}
    
    async def _run_agent_critique(self, state: ResearchState, agent_config: AgentConfig) -> Dict[str, str]:
        """Run a single agent's critique of the draft report."""
        agent = AgentNode(self.llm_client, agent_config)
        result = await agent.critique_draft(state)
        return result.get("draft_critiques", {})
    
    async def _evaluate_phase(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 4: DECISION - Orchestrator evaluates and decides.
        """
        console.print(f"\n{'='*60}")
        console.print("Phase 4: EVALUATION (Orchestrator)")
        console.print(f"{'='*60}")
        
        return await self.orchestrator.evaluate_consensus(state)
    
    def _decision_router(self, state: ResearchState) -> str:
        """Route to loop or finalize based on consensus status."""
        if state.consensus_status == "REACHED":
            return "finalize"
        if state.current_iteration >= state.max_iterations:
            return "finalize"
        return "loop"
    
    async def _synthesize_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Final report synthesis."""
        console.print(f"\n{'='*60}")
        console.print("FINAL: Report Generation")
        console.print(f"{'='*60}")
        return await self.synthesizer.generate_report(state)
    
    def run(self, topic: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Run the research workflow with 4-phase iteration loop.
        """
        initial_state = ResearchState(
            topic=topic,
            config=self.config,
            max_iterations=self.config.get("research", {}).get("max_iterations", 3),
            min_iterations=1,
            status="initialized",
            start_time=datetime.now().isoformat(),
        )
        
        try:
            print(f"\n{'='*60}")
            print("Starting V2 Research Workflow - Design B.1")
            print("4-Phase: Research → Synthesis → Critique → Decision")
            print(f"{'='*60}")
            print(f"Topic: {topic}")
            
            # Phase 0: Team Generation
            print("\n[Setup] Dynamic Team Generation")
            team_result = asyncio.run(self.orchestrator.propose_team(initial_state))
            team_manifest = team_result["team_manifest"]
            initial_state.team_manifest = team_manifest
            
            print(f"\n[[cyan]Orchestrator[/cyan]]: Generated team with {len(team_manifest)} agents:")
            for i, agent in enumerate(team_manifest, 1):
                print(f"  {i}. {agent.role} ({agent.domain})")
            
            # HITL: Team approval
            print(f"\n{'='*60}")
            print("HUMAN INTERVENTION REQUIRED")
            print(f"{'='*60}")
            
            response = console.input(
                "\n[bold]Approve this team? (y/n/add <role>):[/bold] "
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
                print(f"[[cyan]Orchestrator[/cyan]]: Added {new_role}")
            elif response not in ("y", "yes"):
                print("[[cyan]Orchestrator[/cyan]]: Using proposed team")
            
            initial_state.team_approved = True
            initial_state.team_manifest = team_manifest
            
            # Build and run graph
            self.graph = self._build_graph()
            
            run_config = {
                "configurable": {
                    "thread_id": f"research_{topic[:20]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }
            }
            
            result = asyncio.run(self._run_graph(initial_state, run_config))
            
            # Save report
            report_path = self._save_report(topic, result)
            
            return {
                "status": "completed",
                "topic": topic,
                "iterations": result.current_iteration,
                "consensus_status": result.consensus_status,
                "agent_outputs": result.agent_outputs,
                "draft_report": result.draft_report,
                "team_manifest": [{"role": a.role, "domain": a.domain} for a in result.team_manifest],
                "report_path": report_path,
            }
            
        except Exception as e:
            print(f"\n[Error] {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "error": str(e)}
    
    async def _run_graph(self, initial_state: ResearchState, run_config: Dict) -> ResearchState:
        """Run the compiled graph."""
        result = await self.graph.ainvoke(initial_state, run_config)
        if isinstance(result, dict):
            return ResearchState(**result)
        return result
    
    def _save_report(self, topic: str, state: ResearchState) -> str:
        """Save the final report with all supporting materials."""
        import re
        from pathlib import Path
        
        safe_topic = re.sub(r'[^\w\s-]', '', topic)
        safe_topic = re.sub(r'[-\s]+', '-', safe_topic).lower()[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{safe_topic}_{timestamp}.md"
        
        output_dir = self.config.get("output", {}).get("directory", "reports")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filepath = output_path / filename
        
        # Use the final report from the Synthesizer agent
        final_report = getattr(state, 'final_report', '')
        if not final_report:
            final_report = f"# Research Report: {topic}\n\nError: No final report generated."
        
        # Get draft and critiques for appendix
        draft = getattr(state, 'draft_report', '')
        critiques = getattr(state, 'draft_critiques', {})
        
        # Build full document
        lines = [
            f"---",
            f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"topic: {topic}",
            f"iterations: {state.current_iteration}",
            f"consensus_status: {state.consensus_status}",
            f"team: {', '.join(a.role for a in state.team_manifest)}",
            f"---",
            f"",
            f"# FINAL REPORT",
            f"",
            final_report,
        ]
        
        # Add development appendices if enabled
        if self.INCLUDE_DEV_APPENDICES:
            # Add draft report as appendix
            if draft:
                lines.extend([
                    f"",
                    f"---",
                    f"",
                    f"# APPENDIX A: Draft Report",
                    f"",
                    f"The following was the Orchestrator's draft report that was critiqued by agents:",
                    f"",
                    draft,
                ])
            
            # Add critiques as appendix
            if critiques:
                lines.extend([
                    f"",
                    f"---",
                    f"",
                    f"# APPENDIX B: Agent Critiques of Draft",
                    f"",
                ])
                for agent, critique in critiques.items():
                    lines.extend([
                        f"## {agent}",
                        f"",
                        critique,
                        f"",
                    ])
            
            # Add raw agent outputs as final appendix
            lines.extend([
                f"",
                f"---",
                f"",
                f"# APPENDIX C: Raw Agent Research Outputs",
                f"",
            ])
            for role, output in state.agent_outputs.items():
                if "_critique" not in role:
                    lines.extend([
                        f"## {role}",
                        f"",
                        output,
                        f"",
                    ])
        
        content = "\n".join(lines)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        console.print(f"\n[[cyan]Synthesizer[/cyan]]: Report saved to: {filepath}")
        return str(filepath)
