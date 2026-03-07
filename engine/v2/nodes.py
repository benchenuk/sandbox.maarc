"""
V2 Graph Nodes
Implementation of Iteration 3: Parallel Execution with 4-Phase Loop
"""

from typing import Any, Dict, List, Optional
import logging
import json
import re

from engine.v2.state import ResearchState, AgentConfig
from engine.v2.prompts import (
    TEAM_GENERATION_SYSTEM_PROMPT,
    TEAM_GENERATION_PROMPT,
    AGENT_SYSTEM_PROMPT,
    DRAFT_REPORT_SYSTEM_PROMPT,
    DRAFT_REPORT_PROMPT,
    AGENT_RESEARCH_PROMPT,
    AGENT_CRITIQUE_PROMPT,
    AGENT_CRITIQUE_DRAFT_PROMPT,
    FINAL_REPORT_SYSTEM_PROMPT,
    FINAL_REPORT_PROMPT,
    EVALUATE_CONSENSUS_SYSTEM_PROMPT,
    EVALUATE_CONSENSUS_PROMPT,
    REPLAN_TEAM_SYSTEM_PROMPT,
    REPLAN_TEAM_PROMPT,
)
from engine.v2.formatting import format_team_pane, format_takeaways_pane, format_agent_summaries_pane
from engine.v2.parsing import parse_json_response
from engine.models.llm_client import LLMClient

logger = logging.getLogger("engine.nodes")

def save_debug_output(state: ResearchState, prefix: str, content: str, logger_func=None):
    # Check app-level 'debug' for save_output flag
    save_enabled = state.config.get("app", {}).get("debug", {}).get("save_output")
    
    if not save_enabled:
        return
    
    import os
    from pathlib import Path
    from datetime import datetime
    
    debug_dir = Path.home() / ".maarc" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = debug_dir / f"{prefix}_{timestamp}.md"
    
    if logger_func:
        logger_func(f"[dim]Saving debug output to {filepath.name}...[/dim]")
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        if logger_func:
            logger_func(f"[dim]Debug output saved.[/dim]")
    except Exception as e:
        if logger_func:
            logger_func(f"[red]Failed to save debug output: {e}[/red]")


class OrchestratorNode:
    """Orchestrator node - manages the research workflow"""
    
    def __init__(self, llm_client: LLMClient, hub: Optional[Any] = None):
        self.llm_client = llm_client
        self.hub = hub

    def _log(self, message: str, level: str = "info"):
        """Log via Hub if available, fallback to standard logging."""
        if self.hub:
            self.hub.publish("log", message=message)
        else:
            getattr(logger, level)(message)

    def _update_status(self, role: str, status: str):
        """Update agent status via Hub."""
        if self.hub:
            self.hub.publish("agent_update", role=role, status=status)
    
    async def plan_team(self, state: ResearchState) -> Dict[str, Any]:
        """
        Propose a team of agents for the research topic.
        """
        self._update_status("ORCHESTRATOR", "planning")
        try:
            self._log(f"[magenta]Orchestrator[/magenta]: planning team for iteration {state.current_iteration}")
            
            # Generate team using LLM
            prompt = TEAM_GENERATION_PROMPT.format(topic=state.topic)
            
            # Get model from config for team generation
            from engine.utils.config import get_orchestrator_provider
            orch_provider, _ = get_orchestrator_provider(state.config)
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=TEAM_GENERATION_SYSTEM_PROMPT,
                provider=orch_provider,
                temperature=state.config.get("orchestrator", {}).get("temperature", 0.7),
                max_tokens=1500
            )
            
            team = self._parse_and_configure_team(response, state)
            
            return {
                "team_manifest": team,
                "status": "planning",
            }
        finally:
            self._update_status("ORCHESTRATOR", "idle")
            
    async def replan_team(self, state: ResearchState) -> Dict[str, Any]:
        """
        Replan the team for iteration > 1 using the updated draft report.
        """
        self._update_status("ORCHESTRATOR", "planning")
        try:
            self._log(f"[magenta]Orchestrator[/magenta]: replanning team for iteration {state.current_iteration}")
            
            prev_team_text = json.dumps([{"role": a.role, "domain": a.domain, "goal": a.goal} for a in state.team_manifest], indent=2)
            
            # Calculate iterations remaining
            iterations_remaining = state.max_iterations - state.current_iteration
            
            prompt = REPLAN_TEAM_PROMPT.format(
                topic=state.topic,
                iteration=state.current_iteration,
                max_iterations=state.max_iterations,
                iterations_remaining=iterations_remaining,
                draft_report=state.draft_report,
                previous_team=prev_team_text
            )
            
            from engine.utils.config import get_orchestrator_provider
            orch_provider, _ = get_orchestrator_provider(state.config)
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=REPLAN_TEAM_SYSTEM_PROMPT,
                provider=orch_provider,
                temperature=state.config.get("orchestrator", {}).get("temperature", 0.7),
                max_tokens=1500
            )
            
            team = self._parse_and_configure_team(response, state)
            
            return {
                "team_manifest": team,
                "status": "researching",
            }
        finally:
            self._update_status("ORCHESTRATOR", "idle")

    def _parse_and_configure_team(self, response: str, state: ResearchState) -> List[AgentConfig]:
        """
        Shared logic for parsing LLM response into a list of AgentConfig objects.
        """
        # Parse JSON response
        try:
            # Extract JSON from response (handle potential markdown code blocks)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            
            team_data = json.loads(json_str)
            
            if not isinstance(team_data, list):
                raise ValueError("Expected JSON array of agents")
            
            # Additional check: ensure elements are dictionaries
            if any(not isinstance(agent, dict) for agent in team_data):
                raise ValueError("Expected JSON array to contain agent objects, but found other types")
            
        except (json.JSONDecodeError, ValueError) as e:
            self._log(f"[red]Orchestrator: failed to parse team JSON: {e}[/red]")
            # Save failed response for debugging
            save_debug_output(state, f"failed_team_response_iter_{state.current_iteration}", response, self._log)
            # Fail the application
            raise ValueError(f"Failed to parse team JSON from Orchestrator: {e}")

        # Get team generation constraints
        team_gen = state.config.get("orchestrator", {}).get("team_generation", {})
        max_agents = team_gen.get("max_agents", 5)
        
        # Enforce max_agents limit
        if len(team_data) > max_agents:
            team_data = team_data[:max_agents]
        
        # Convert to AgentConfig objects with generated system prompts
        from engine.utils.config import get_agent_providers, get_provider_config
        agent_providers = get_agent_providers(state.config)
        agent_cfg = agent_providers.get("default", {})
        agent_prov = agent_cfg.get("provider")
        prov_cfg = get_provider_config(state.config, agent_prov)
        agent_model = prov_cfg.get("default_model", "gpt-4o")

        team = []
        for agent_data in team_data:
            role = agent_data.get("role", "Expert")
            domain = agent_data.get("domain", "General")
            goal = agent_data.get("goal", "Analyze the topic")
            
            # Generate system prompt for this role
            system_prompt = self._generate_system_prompt(role, domain, goal)
            
            team.append(AgentConfig(
                role=role,
                domain=domain,
                goal=goal,
                system_prompt=system_prompt,
                provider=agent_prov,
                model=agent_model,
                temperature=agent_cfg.get("temperature", 0.7) if "skeptic" not in role.lower() else 0.8
            ))
        
        self._log(f"Team: {', '.join(a.role for a in team)}")
        self._log(format_team_pane(team_data))
        
        return team
    
    def _generate_system_prompt(self, role: str, domain: str, goal: str) -> str:
        """Generate a system prompt for an agent based on its configuration."""
        return AGENT_SYSTEM_PROMPT.format(role=role, domain=domain, goal=goal)
    
    async def draft_report(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 2: Create comprehensive draft report from all research.
        """
        self._update_status("ORCHESTRATOR", "drafting")
        try:
            self._log("[magenta]Orchestrator[/magenta]: drafting report")
            
            # Gather all research outputs (not critiques)
            research_outputs = []
            for role, output in state.agent_outputs.items():
                if "_critique_" not in role and "_critique" not in role:
                    research_outputs.append(f"## {role}\n{output}")
            
            draft_prompt = DRAFT_REPORT_PROMPT.format(
                topic=state.topic,
                iteration=state.current_iteration,
                research_outputs="\n".join(research_outputs),
            )

            from engine.utils.config import get_orchestrator_provider
            orch_provider, _ = get_orchestrator_provider(state.config)
            
            draft = await self.llm_client.complete(
                prompt=draft_prompt,
                system_prompt=DRAFT_REPORT_SYSTEM_PROMPT,
                provider=orch_provider,
                temperature=0.4,  # Lower temp for consistent structure
                max_tokens=2500
            )
            
            # Parse unified JSON response
            report_content = ""
            takeaways = []
            
            try:
                # Extract JSON from potential code blocks
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', draft, re.DOTALL)
                json_str = json_match.group(1) if json_match else draft
                
                data = json.loads(json_str.strip())
                
                # Robustness check: ensure 'data' is a dictionary
                if isinstance(data, dict):
                    report_content = data.get("draft_report", "")
                    takeaways = data.get("key_takeaways", [])
                else:
                    self._log(f"[yellow]Orchestrator: LLM returned JSON {type(data).__name__} instead of dict. Attempting fallback.[/yellow]")
                    report_content = draft
                    takeaways = []
                
                if not report_content:
                    # Fallback if structure is wrong but text is there
                    report_content = draft
            except Exception as e:
                self._log(f"[red]Orchestrator: failed to parse unified JSON: {e}[/red]")
                # Last resort fallback: treat entire response as report
                report_content = draft

            save_debug_output(state, "draft_report", report_content, self._log)

            self._log(f"[magenta]Orchestrator[/magenta]: draft done ({len(report_content)} chars)")
            
            if takeaways:
                self._log(f"[dim]Summarised in {len(takeaways)} key takeaways ...[/dim]")
                self._log(format_takeaways_pane(takeaways))

            return {
                "draft_report": report_content,
                "key_takeaways": takeaways,
                "status": "critiquing",
            }
        finally:
            self._update_status("ORCHESTRATOR", "idle")
    
    async def evaluate_consensus(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 4: Evaluate if consensus has been reached.
        """
        self._update_status("ORCHESTRATOR", "evaluating")
        try:
            new_iteration = state.current_iteration + 1
            
            # Check if we should stop
            if new_iteration > state.max_iterations:
                self._log("[dim]Max iterations reached[/dim]")
                return {
                    "current_iteration": state.current_iteration, # Keep the last valid one if we stop
                    "consensus_status": "REACHED",
                    "status": "completed",
                }
            
            self._log(f"[magenta]Orchestrator[/magenta]: evaluating consensus")
            
            # Format critiques
            critiques_text = []
            for role, critique in getattr(state, 'draft_critiques', {}).items():
                critiques_text.append(f"## Critique from {role}\n{critique}")
                
            # Calculate iterations remaining
            iterations_remaining = state.max_iterations - state.current_iteration
            
            prompt = EVALUATE_CONSENSUS_PROMPT.format(
                topic=state.topic,
                iteration=state.current_iteration,
                max_iterations=state.max_iterations,
                iterations_remaining=iterations_remaining,
                draft_report=state.draft_report,
                critiques="\n\n".join(critiques_text) if critiques_text else "No critiques provided."
            )
            
            from engine.utils.config import get_orchestrator_provider
            orch_provider, _ = get_orchestrator_provider(state.config)
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=EVALUATE_CONSENSUS_SYSTEM_PROMPT,
                provider=orch_provider,
                temperature=0.3, # Low temp for precise formatting / evaluation
                max_tokens=2500
            )
            
            try:
                # Extract JSON
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                
                evaluation = json.loads(json_str)
                
                # Robustness check: ensure 'evaluation' is a dictionary
                if not isinstance(evaluation, dict):
                     raise ValueError(f"Expected JSON object for evaluation, but got {type(evaluation).__name__}")
                
                decision = evaluation.get("decision", "IN_PROGRESS")
                updated_draft = evaluation.get("updated_draft", state.draft_report)
                
                if decision == "REACHED":
                    self._log("[green]Consensus REACHED[/green]")
                    
                    # Save the updated draft for debug/record
                    save_debug_output(state, f"draft_report_final_iter_{state.current_iteration}", updated_draft, self._log)
                    
                    return {
                        "current_iteration": new_iteration,
                        "consensus_status": "REACHED",
                        "draft_report": updated_draft,
                        "status": "completed"
                    }
                else:
                    self._log("[yellow]More research needed - updating draft and planning next iteration[/yellow]")
                    
                    # Save the updated draft for debug/record
                    save_debug_output(state, f"draft_report_critiqued_iter_{state.current_iteration}", updated_draft, self._log)
                    
                    return {
                        "current_iteration": new_iteration,
                        "consensus_status": "IN_PROGRESS",
                        "draft_report": updated_draft, # Replace draft with the newly updated one incorporate critiques
                        "status": "planning",
                    }
                    
            except (json.JSONDecodeError, ValueError) as e:
                self._log(f"[red]Orchestrator: failed to parse evaluation JSON: {e}[/red]")
                # Save failed response for debugging
                # save_debug_output(state, f"failed_evaluation_response_iter_{state.current_iteration}", response, self._log)
                
                # Fallback to loop if we can't parse, just returning old draft
                return {
                    "current_iteration": new_iteration,
                    "consensus_status": "IN_PROGRESS",
                    "status": "planning"
                }

        finally:
            self._update_status("ORCHESTRATOR", "idle")


class AgentNode:
    """Generic agent node that adapts based on agent configuration"""
    
    def __init__(self, llm_client: LLMClient, agent_config: AgentConfig, hub: Optional[Any] = None):
        self.llm_client = llm_client
        self.config = agent_config
        self.hub = hub

    def _log(self, message: str, level: str = "info"):
        if self.hub:
            self.hub.publish("log", message=message)
        else:
            getattr(logger, level)(message)

    def _update_status(self, status: str):
        if self.hub:
            self.hub.publish("agent_update", role=self.config.role, status=status)
    
    async def research(self, state: ResearchState) -> Dict[str, Any]:
        """
        Conduct initial research on the topic.
        """
        self._update_status("researching")
        try:
            self._log(f"[cyan]{self.config.role}[/cyan]: starting research")
            
            draft_ctx = ""
            if getattr(state, "draft_report", ""):
                 draft_ctx = f"\n--- CURRENT DRAFT REPORT ---\n{state.draft_report}\n--- END DRAFT REPORT ---\n"
            
            prompt = AGENT_RESEARCH_PROMPT.format(
                topic=state.topic,
                role=self.config.role,
                domain=self.config.domain,
                goal=self.config.goal,
                draft_context=draft_ctx
            )
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                provider=self.config.provider,
                model=self.config.model,
                temperature=self.config.temperature,
            )
            
            output_key = self.config.role
            
            # Sanitization of role is already handled by AgentConfig pydantic validation
            save_debug_output(state, f"agent_research_{self.config.role}", response, self._log)
            
            # Parse JSON response to extract main content and summary
            research_result, executive_summary = parse_json_response(
                response, 
                main_field="main",
                summary_field="summary",
                fallback=response
            )
            
            self._log(f"[cyan]{self.config.role}[/cyan]: done ({len(research_result)} chars)")
            
            return {
                "agent_outputs": {output_key: research_result},
                "agent_summaries": {output_key: executive_summary} if executive_summary else {}
            }
        finally:
            self._update_status("idle")
    
    async def critique(self, state: ResearchState, target_role: str) -> Dict[str, Any]:
        """
        Critique another agent's output.
        """
        self._update_status("critiquing")
        try:
            target_output = state.get_agent_output(target_role)
            if not target_output:
                return {"agent_outputs": {}}
            
            self._log(f"Critiquing {target_role}...")
            
            prompt = AGENT_CRITIQUE_PROMPT.format(
                topic=state.topic,
                target_role=target_role,
                target_output=target_output,
                role=self.config.role,
                domain=self.config.domain,
                goal=self.config.goal,
            )
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                provider=self.config.provider,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=600
            )
            
            # Store critique with key indicating source and target
            output_key = f"{self.config.role}_critique_of_{target_role}"
            self._log(f"Critique complete ({len(response)} chars)")
            
            return {
                "agent_outputs": {output_key: response}
            }
        finally:
            self._update_status("idle")
    
    async def critique_draft(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 3: Critique the orchestrator's draft report.
        """
        self._update_status("critiquing")
        try:
            draft = getattr(state, 'draft_report', '')
            if not draft:
                return {"draft_critiques": {}}
            
            self._log(f"[yellow]{self.config.role}[/yellow]: starting critique")
            
            prompt = AGENT_CRITIQUE_DRAFT_PROMPT.format(
                topic=state.topic,
                draft=draft,
                role=self.config.role,
                domain=self.config.domain,
                goal=self.config.goal,
            )
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                provider=self.config.provider,
                model=self.config.model,
                temperature=self.config.temperature,
            )
            
            save_debug_output(state, f"agent_critique_{self.config.role}", response, self._log)
            
            # Parse JSON response to extract main content and summary
            critique, actionables = parse_json_response(
                response,
                main_field="main",
                summary_field="summary",
                fallback=response
            )
            
            self._log(f"[yellow]{self.config.role}[/yellow]: done ({len(critique)} chars)")
            
            return {
                "draft_critiques": {self.config.role: critique},
                "critique_summaries": {self.config.role: actionables} if actionables else {}
            }
        finally:
            self._update_status("idle")


class SynthesisNode:
    """
    Synthesizer Agent - Generates comprehensive final report using LLM.
    """
    
    def __init__(self, llm_client: LLMClient, hub: Optional[Any] = None):
        self.llm_client = llm_client
        self.hub = hub

    def _log(self, message: str, level: str = "info"):
        if self.hub:
            self.hub.publish("log", message=message)
        else:
            getattr(logger, level)(message)
    
    async def generate_report(self, state: ResearchState) -> Dict[str, Any]:
        """Generate comprehensive final report using the latest draft report."""
        if self.hub:
            self.hub.publish("agent_update", role="SYNTHESIZER", status="synthesizing")
        try:
            self._log("[magenta]Synthesizer[/magenta]: generating final report")
            
            # Get draft report which now incorporates all research and critiques
            draft_report = getattr(state, 'draft_report', '')
            
            # Build synthesis prompt
            prompt = FINAL_REPORT_PROMPT.format(
                topic=state.topic,
                iteration=state.current_iteration,
                consensus_status=state.consensus_status,
                draft_report=draft_report if draft_report else "[No draft available]",
            )

            # Get synthesizer config
            synth_config = state.config.get("synthesizer", {})
            synth_provider = synth_config.get("provider")
            synth_temp = synth_config.get("temperature", 0.3)
            
            # Generate report via LLM
            report_content = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=FINAL_REPORT_SYSTEM_PROMPT,
                provider=synth_provider,
                temperature=synth_temp,
                max_tokens=4000
            )
            
            self._log(f"[magenta]Synthesizer[/magenta]: done ({len(report_content)} chars)")
            
            return {
                "final_report": report_content,
                "status": "completed",
                "end_time": __import__('datetime').datetime.now().isoformat(),
            }
        finally:
            if self.hub:
                self.hub.publish("agent_update", role="SYNTHESIZER", status="idle")
