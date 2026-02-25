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
    TEAM_GENERATION_PROMPT,
    AGENT_SYSTEM_PROMPT,
    DRAFT_REPORT_PROMPT,
    AGENT_RESEARCH_PROMPT,
    AGENT_CRITIQUE_PROMPT,
    AGENT_DRAFT_CRITIQUE_PROMPT,
    FINAL_REPORT_PROMPT,
)
from engine.models.llm_client import LLMClient

logger = logging.getLogger("engine.nodes")


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
    
    async def propose_team(self, state: ResearchState) -> Dict[str, Any]:
        """
        Propose a team of agents for the research topic.
        Iteration 2: Uses LLM to dynamically generate domain-specific team.
        """
        self._update_status("ORCHESTRATOR", "planning")
        try:
            self._log(f"[magenta]Orchestrator[/magenta]: planning team")
            
            # Generate team using LLM
            prompt = TEAM_GENERATION_PROMPT.format(topic=state.topic)
            
            # Get model from config for team generation
            from engine.utils.config import get_orchestrator_provider
            orch_provider, _ = get_orchestrator_provider(state.config)
            
            response = await self.llm_client.complete(
                prompt=prompt,
                provider=orch_provider,
                temperature=state.config.get("orchestrator", {}).get("temperature", 0.7),
                max_tokens=1500
            )
            
            # Parse JSON response
            import json
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
                
            except (json.JSONDecodeError, ValueError) as e:
                self._log(f"[yellow]Orchestrator: fallback team[/yellow]")
                self._log(f"[dim]Reason: {e}[/dim]")
                # Log the raw response (truncated if too long)
                response_preview = response[:500] + "..." if len(response) > 500 else response
                self._log(f"[dim]LLM response: {response_preview}[/dim]")
                # Fallback to default team
                team_data = [
                    {"role": "Domain Expert", "domain": "General Analysis", "goal": "Provide comprehensive analysis"},
                    {"role": "Skeptic", "domain": "Critical Analysis", "goal": "Challenge assumptions and identify risks"}
                ]
            
            # Get team generation constraints
            team_gen = state.config.get("orchestrator", {}).get("team_generation", {})
            min_agents = team_gen.get("min_agents", 3)
            max_agents = team_gen.get("max_agents", 5)
            require_skeptic = team_gen.get("require_skeptic", True)
            
            # Enforce max_agents limit
            if len(team_data) > max_agents:
                team_data = team_data[:max_agents]
            
            # Check for skeptic
            has_skeptic = any("skeptic" in str(a.get("role", "")).lower() for a in team_data)
            if require_skeptic and not has_skeptic:
                team_data.append({
                    "role": "Skeptic",
                    "domain": "Critical Analysis",
                    "goal": "Challenge assumptions and identify risks"
                })
            
            # Enforce min_agents by adding generic experts if needed
            while len(team_data) < min_agents:
                team_data.append({
                    "role": f"Domain Expert {len(team_data)}",
                    "domain": "General Analysis",
                    "goal": "Provide additional perspective"
                })
            
            # Convert to AgentConfig objects with generated system prompts
            team = []
            for agent_data in team_data:
                role = agent_data.get("role", "Expert")
                domain = agent_data.get("domain", "General")
                goal = agent_data.get("goal", "Analyze the topic")
                
                # Generate system prompt for this role
                system_prompt = self._generate_system_prompt(role, domain, goal)
                
                # Get agent provider config for spawned agents
                from engine.utils.config import get_agent_providers, get_provider_config
                agent_providers = get_agent_providers(state.config)
                agent_cfg = agent_providers.get("default", {})
                agent_prov = agent_cfg.get("provider")
                
                prov_cfg = get_provider_config(state.config, agent_prov)
                agent_model = prov_cfg.get("default_model", "gpt-4o")
                
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
            
            # Log team details with subtle background shading in a uniform pane
            import textwrap
            
            # 1. Calculate ideal pane width based on content, with a min/max bound
            max_natural = max((len(f"{a.get('role', 'Expert')} — {a.get('goal', 'Analyze the topic')}") for a in team_data), default=0)
            pane_width = min(max(max_natural + 6, 100), 140)
            text_width = pane_width - 4
            
            bg_style = "on grey23"
            text_style = "grey82"
            
            # 2. Build the pane
            team_lines = [f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]"]
            for agent_data in team_data:
                role = agent_data.get("role", "Expert")
                goal = agent_data.get("goal", "Analyze the topic")
                
                # 1. Role Line (Bold)
                padding_role = " " * (pane_width - (len(role) + 2))
                team_lines.append(f"[{text_style} {bg_style}]  [bold]{role}[/bold]{padding_role}[/{text_style} {bg_style}]")
                
                # 2. Goal Text (Wrapped)
                wrapped_goal = textwrap.wrap(goal, width=text_width)
                for line in wrapped_goal:
                    content = f"  {line}"
                    padding = " " * (pane_width - len(content))
                    team_lines.append(f"[{text_style} {bg_style}]{content}{padding}[/{text_style} {bg_style}]")
                
                # 3. Add a small gap between agents (except maybe the last one)
                team_lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
            
            team_lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
            
            self._log("\n".join(team_lines))
            
            return {
                "team_manifest": team,
                "status": "planning",
            }
        finally:
            self._update_status("ORCHESTRATOR", "idle")
    
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
                provider=orch_provider,
                temperature=0.4,  # Lower temp for consistent structure
                max_tokens=2500
            )
            
            # Parse JSON takeaways from draft
            takeaways = []
            try:
                # 1. Try to find structured JSON in markdown blocks
                json_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', draft, re.DOTALL)
                
                # 2. If no backticks, try a raw search for the pattern
                if not json_blocks:
                    # Look for anything that starts with { and has key_takeaways in it
                    # Greedy match from first { to last } that contains key_takeaways
                    raw_match = re.search(r'(\{.*"key_takeaways".*\})', draft, re.DOTALL)
                    if raw_match:
                        json_blocks = [raw_match.group(1)]


                for block in reversed(json_blocks):
                    try:
                        data = json.loads(block.strip())
                        if isinstance(data, dict) and "key_takeaways" in data:
                            takeaways = data["key_takeaways"]
                            break
                    except json.JSONDecodeError:
                        continue
                
                if not takeaways:
                    # FALLBACK: Try to find a bulleted list under a "Key Takeaways" header
                    # This handles cases where the LLM ignores the JSON instruction but follows the report structure
                    takeaways_match = re.search(r'## Key Takeaways\n(.*?)(?:\n##|\Z)', draft, re.DOTALL | re.IGNORECASE)
                    if takeaways_match:
                        list_text = takeaways_match.group(1).strip()
                        # Extract lines starting with - or • or numbering
                        lines = re.findall(r'(?:^|\n)\s*[•\-\*]\s*(.+)', list_text)
                        if lines:
                            takeaways = [l.strip() for l in lines]

                if not takeaways:
                    self._log("[yellow]Orchestrator: skipped takeaways pane (none parsed from JSON or text)[/yellow]")
            except Exception as e:
                self._log(f"[red]Orchestrator: error in takeaway parser: {e}[/red]")
                # Fallback: if JSON parsing fails, we don't log takeaways block
                pass

            self._log(f"[magenta]Orchestrator[/magenta]: draft done ({len(draft)} chars)")
            
            if takeaways:
                self._log(f"[dim]Found {len(takeaways)} key takeaways. Formatting pane...[/dim]")
                import textwrap
                
                # Calculate ideal pane width based on content
                max_natural = max((len(f"• {t}") for t in takeaways), default=0)
                pane_width = min(max(max_natural + 8, 100), 140)
                text_width = pane_width - 8  # Account for margins and bullets
                
                bg_style = "on grey23"
                text_style = "grey82"
                
                takeaway_lines = [f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]"]
                # Header
                takeaway_lines.append(f"[{text_style} {bg_style}]  [bold]Key Takeaways:[/bold]{' ' * (pane_width - 17)}[/{text_style} {bg_style}]")
                takeaway_lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
                
                for t in takeaways:
                    # Wrap the takeaway text to fit the pane
                    wrapped_lines = textwrap.wrap(t, width=text_width)
                    for i, line in enumerate(wrapped_lines):
                        prefix = "  • " if i == 0 else "    "
                        content = f"{prefix}{line}"
                        padding = " " * (pane_width - len(content))
                        takeaway_lines.append(f"[{text_style} {bg_style}]{content}{padding}[/{text_style} {bg_style}]")
                
                takeaway_lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
                
                self._log("\n".join(takeaway_lines))

            return {
                "draft_report": draft,
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
            if new_iteration >= state.max_iterations:
                self._log("[dim]Max iterations reached[/dim]")
                return {
                    "current_iteration": new_iteration,
                    "consensus_status": "REACHED",
                    "status": "completed",
                }
            
            # For now, simple logic: continue looping
            self._log("More research needed - will assemble team for next iteration")
            return {
                "current_iteration": new_iteration,
                "consensus_status": "IN_PROGRESS",
                "status": "planning",  # Will trigger new team assembly
            }
        finally:
            self._update_status("ORCHESTRATOR", "Idle")


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
        self._update_status("research")
        try:
            self._log(f"[cyan]{self.config.role}[/cyan]: starting research")
            
            prompt = AGENT_RESEARCH_PROMPT.format(
                topic=state.topic,
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
                max_tokens=800
            )
            
            output_key = self.config.role
            self._log(f"[cyan]{self.config.role}[/cyan]: done ({len(response)} chars)")
            
            return {
                "agent_outputs": {output_key: response}
            }
        finally:
            self._update_status("idle")
    
    async def critique(self, state: ResearchState, target_role: str) -> Dict[str, Any]:
        """
        Critique another agent's output.
        """
        self._update_status("Working")
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
            self._update_status("Idle")
    
    async def critique_draft(self, state: ResearchState) -> Dict[str, Any]:
        """
        Phase 3: Critique the orchestrator's draft report.
        """
        self._update_status("critique")
        try:
            draft = getattr(state, 'draft_report', '')
            if not draft:
                return {"draft_critiques": {}}
            
            self._log(f"[yellow]{self.config.role}[/yellow]: starting critique")
            
            prompt = AGENT_DRAFT_CRITIQUE_PROMPT.format(
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
                max_tokens=800
            )
            
            self._log(f"[yellow]{self.config.role}[/yellow]: done ({len(response)} chars)")
            
            return {
                "draft_critiques": {self.config.role: response}
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
        """Generate comprehensive final report using all available inputs."""
        if self.hub:
            self.hub.publish("agent_update", role="SYNTHESIZER", status="working")
        try:
            self._log("[magenta]Synthesizer[/magenta]: generating final report")
            
            # Gather all research outputs (not critiques)
            research_outputs = []
            for role, output in state.agent_outputs.items():
                if "_critique" not in role and "_critique" not in role:
                    research_outputs.append(f"### {role}\n{output}")
            
            # Get draft report and critiques
            draft_report = getattr(state, 'draft_report', '')
            draft_critiques = getattr(state, 'draft_critiques', {})
            
            # Format critiques
            critiques_text = []
            for agent, critique in draft_critiques.items():
                critiques_text.append(f"### Critique from {agent}\n{critique}")
            
            # Build synthesis prompt
            critiques_text_str = "\n".join(critiques_text) if critiques_text else "No critiques recorded."
            prompt = FINAL_REPORT_PROMPT.format(
                topic=state.topic,
                iteration=state.current_iteration,
                consensus_status=state.consensus_status,
                research_outputs="\n".join(research_outputs),
                draft_report=draft_report if draft_report else "[No draft available]",
                critiques=critiques_text_str,
            )

            # Get synthesizer config
            synth_config = state.config.get("synthesizer", {})
            synth_provider = synth_config.get("provider")
            synth_temp = synth_config.get("temperature", 0.3)
            
            # Generate report via LLM
            report_content = await self.llm_client.complete(
                prompt=prompt,
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
