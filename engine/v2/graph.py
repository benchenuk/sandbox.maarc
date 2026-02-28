"""
V2 Graph Definition - Iteration 3: Parallel Execution with 4-Phase Loop
LangGraph implementation with hybrid parallel-sequential pattern

Design B.1: Research → Synthesis → Critique → Decision
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from engine.v2.state import ResearchState, AgentConfig
from engine.v2.nodes import OrchestratorNode, AgentNode, SynthesisNode
from engine.models.llm_client import LLMClient
from rich.console import Console

# Import EventHub from the package it belongs to
try:
    from maarc.hub import EventHub
except ImportError:
    EventHub = Any  # Fallback for non-TUI usage


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
    
    def __init__(self, config: Dict[str, Any], hub: Optional[Any] = None):
        self.config = config
        self.llm_client = LLMClient(config)
        self.hub = hub
        
        # Initialize nodes
        self.orchestrator = OrchestratorNode(self.llm_client, hub=self.hub)
        self.synthesizer = SynthesisNode(self.llm_client, hub=self.hub)

    def _log(self, message: str):
        """Helper to log via Hub if available, otherwise print."""
        if self.hub:
            self.hub.publish("log", message=message)
        else:
            print(message)

    def _update_phase(self, name: str):
        """Signal a phase transition to the UI."""
        if self.hub:
            self.hub.publish("phase_update", name=name)
        self._log(f"Phase: [b]{name.lower()}[/b]")

    def _update_agent_status(self, role: str, status: str):
        """Signal an agent status change."""
        if self.hub:
            self.hub.publish("agent_update", role=role, status=status)

    def _update_iteration(self, current: int, total: int):
        """Signal iteration count change."""
        if self.hub:
            self.hub.publish("iteration_update", current=current, total=total)
    
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
        """Phase entry: Prepare for this iteration."""
        next_iter = state.current_iteration + (1 if state.current_iteration == 0 else 0)
        self._update_iteration(next_iter, state.max_iterations)
        self._update_phase("planning")
        
        if state.current_iteration == 0:
            state.current_iteration += 1
            team_result = await self.orchestrator.plan_team(state)
            team_manifest = team_result.get("team_manifest", [])
            
            if self.hub:
                self.hub.publish("team_update", agents=[{"role": a.role, "domain": a.domain} for a in team_manifest])
                
            return {
                "current_iteration": 1, 
                "status": "researching", 
                "team_manifest": team_manifest,
                "team_approved": True
            }
        else:
            team_result = await self.orchestrator.replan_team(state)
            team_manifest = team_result.get("team_manifest", [])
            
            if self.hub:
                self.hub.publish("team_update", agents=[{"role": a.role, "domain": a.domain} for a in team_manifest])
                
            return {
                "status": "researching", 
                "team_manifest": team_manifest
            }
    
    async def _research_parallel(self, state: ResearchState) -> Dict[str, Any]:
        """Phase 1: RESEARCH - All agents research in parallel."""
        self._update_phase("researching")
        
        tasks = []
        for agent_config in state.team_manifest:
            task = self._run_agent_research(state, agent_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_outputs = {}
        all_summaries = {}
        for agent_config, result in zip(state.team_manifest, results):
            if isinstance(result, Exception):
                self._log(f"[red]{agent_config.role}: error[/red]")
                all_outputs[agent_config.role] = f"Error: {result}"
            else:
                all_outputs.update(result.get("agent_outputs", {}))
                all_summaries.update(result.get("agent_summaries", {}))
        
        self._log(f"Collected {len(all_outputs)} outputs, {len(all_summaries)} summaries")
        
        return {
            "agent_outputs": all_outputs,
            "agent_summaries": all_summaries,
            "status": "synthesizing"
        }
    
    async def _run_agent_research(self, state: ResearchState, agent_config: AgentConfig) -> Dict[str, Any]:
        """Run a single agent's research and display summary immediately."""
        agent = AgentNode(self.llm_client, agent_config, hub=self.hub)
        result = await agent.research(state)
        
        # Display summary immediately as it completes
        agent_summaries = result.get("agent_summaries", {})
        if agent_summaries and agent_config.role in agent_summaries:
            summary = agent_summaries[agent_config.role]
            if summary:
                from engine.v2.formatting import format_agent_summaries_pane
                self._log(format_agent_summaries_pane(
                    {agent_config.role: summary}, 
                    title=f"Summary - {agent_config.role}"
                ))
        
        return {
            "agent_outputs": result.get("agent_outputs", {}),
            "agent_summaries": agent_summaries
        }
    
    async def _draft_report_phase(self, state: ResearchState) -> Dict[str, Any]:
        """Phase 2: DRAFT REPORT - Orchestrator creates comprehensive draft."""
        self._update_phase("drafting")
        self._update_agent_status("ORCHESTRATOR", "drafting")
        
        result = await self.orchestrator.draft_report(state)
        self._update_agent_status("ORCHESTRATOR", "idle")
        return result
    
    async def _critique_parallel(self, state: ResearchState) -> Dict[str, Any]:
        """Phase 3: CRITIQUE - All agents critique the draft report."""
        self._update_phase("critiquing")
        
        tasks = []
        for agent_config in state.team_manifest:
            task = self._run_agent_critique(state, agent_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_critiques = {}
        all_actionables = {}
        for agent_config, result in zip(state.team_manifest, results):
            if isinstance(result, Exception):
                self._log(f"[red]{agent_config.role}: error[/red]")
            else:
                all_critiques.update(result.get("draft_critiques", {}))
                all_actionables.update(result.get("critique_summaries", {}))
        
        self._log(f"Collected {len(all_critiques)} critiques, {len(all_actionables)} actionables")
        
        return {
            "draft_critiques": all_critiques,
            "critique_summaries": all_actionables,
            "status": "evaluating"
        }
    
    async def _run_agent_critique(self, state: ResearchState, agent_config: AgentConfig) -> Dict[str, Any]:
        """Run a single agent's critique and display actionables immediately."""
        agent = AgentNode(self.llm_client, agent_config, hub=self.hub)
        result = await agent.critique_draft(state)
        
        # Display actionables immediately as it completes
        critique_summaries = result.get("critique_summaries", {})
        if critique_summaries and agent_config.role in critique_summaries:
            actionables = critique_summaries[agent_config.role]
            if actionables:
                from engine.v2.formatting import format_agent_summaries_pane
                self._log(format_agent_summaries_pane(
                    {agent_config.role: actionables},
                    title=f"Actionables - {agent_config.role}"
                ))
        
        return {
            "draft_critiques": result.get("draft_critiques", {}),
            "critique_summaries": critique_summaries
        }
    
    async def _evaluate_phase(self, state: ResearchState) -> Dict[str, Any]:
        """Phase 4: DECISION - Orchestrator evaluates and decides."""
        self._update_phase("evaluating")
        self._update_agent_status("ORCHESTRATOR", "evaluating")
        res = await self.orchestrator.evaluate_consensus(state)
        self._update_agent_status("ORCHESTRATOR", "idle")
        return res
    
    def _decision_router(self, state: ResearchState) -> str:
        """Route to loop or finalize based on consensus status."""
        if state.consensus_status == "REACHED":
            return "finalize"
        if state.current_iteration > state.max_iterations:
            return "finalize"
        return "loop"
    
    async def _synthesize_wrapper(self, state: ResearchState) -> Dict[str, Any]:
        """Final report synthesis."""
        self._update_phase("finalizing")
        self._update_agent_status("SYNTHESIZER", "synthesizing")
        res = await self.synthesizer.generate_report(state)
        self._update_agent_status("SYNTHESIZER", "idle")
        return res
    
    async def run(self, topic: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Run the research workflow with 4-phase iteration loop.
        """
        initial_state = ResearchState(
            topic=topic,
            config=self.config,
            max_iterations=self.config.get("research", {}).get("max_iterations", 1), # Default to 1 for safety
            min_iterations=1,
            status="initialized",
            start_time=datetime.now().isoformat(),
        )
        
        try:
            self._update_iteration(0, initial_state.max_iterations)
            
            # Build and run graph
            self.graph = self._build_graph()
            
            run_config = {
                "configurable": {
                    "thread_id": f"research_{topic[:20]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }
            }
            
            result = await self._run_graph(initial_state, run_config)
            
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
            import traceback
            error_trace = traceback.format_exc()
            self._log(f"[red]Error: {str(e)}[/red]")
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
        
        # Always append the original question at the end
        lines.extend([
            f"",
            f"---",
            f"",
            f"# Original Question",
            f"",
            topic,
            f"",
        ])
        
        content = "\n".join(lines)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        self._log(f"\nSynthesizer: Report saved to: {filepath}")
        return str(filepath)
