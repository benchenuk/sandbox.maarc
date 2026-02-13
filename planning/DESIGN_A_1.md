# System Design Report: AI Multi-Agent Researcher (MVP) - Revision 2

## 1. Executive Summary
This revision upgrades the application design to support **Dynamic Role Instantiation**. Instead of relying on a static set of generic agents (Researcher, Skeptic), the Orchestrator will analyze the topic's domain (e.g., Construction, Economics, Software Engineering) to spawn specialized agents with relevant personas, toolsets, and perspectives. The system remains a CLI-based, iterative framework but now features a "Strategy Phase" where the Orchestrator proposes a custom team structure for Human-in-the-Loop approval before execution begins.

## 2. Architecture: Dynamic Agent Spawning

The architecture shifts from a fixed "Hub-and-Spoke" to a **Fluid Team Model**. The Orchestrator acts as a Project Manager, defining the team composition based on the specific question asked.

### 2.1 Core Components Update

1.  **The Strategist (Orchestrator Node):**
    *   **Function:** The first node in the graph. It receives the user's topic and determines the necessary domain perspectives.
    *   **Action:** Outputs a JSON manifest of required agents (e.g., `[{"role": "Structural Engineer", "goal": "Assess load bearing"}, {"role": "Financial Analyst", "goal": "Calculate ROI"}]`).
    *   **Human-in-the-Loop:** Pauses execution to let the user approve, remove, or add agents to the manifest.

2.  **Agent Factory:**
    *   A utility module that reads the JSON manifest.
    *   It dynamically generates system prompts for each role using a "Persona Template" (e.g., *"You are a {role}. Your goal is {goal}. You must strictly focus on {perspective}."*).
    *   It maps these roles to the appropriate model in the Model Pool (e.g., mapping a "Coder" agent to a coding-optimized LLM).

3.  **The Debate Arena (Iterative Loop):**
    *   Instead of a generic debate, this is a domain-specific collision of perspectives.
    *   *Example:* In a construction project, the **Architect** proposes a design; the **Electrician** agent critiques the feasibility of wiring; the **Accountant** critiques the budget. The Orchestrator feeds these specific critiques to the relevant counterpart.

## 3. Framework Recommendation: LangGraph

**LangGraph** remains the strongest recommendation, specifically for its support of **Dynamic Graphs**.

*   **Why it fits:** In CrewAI or AutoGen, defining dynamic agent teams programmatically often requires complex scaffolding or "GroupChat" managers which can get chaotic.
*   **LangGraph Advantage:** You can programmatically generate nodes in the graph based on the output of the "Strategist" node. The `State` object can hold a list of active agents, and the graph edges can dynamically route messages to these specific agents.

## 4. Workflow Design: The "Strategy-Execute" Loop

### Phase 1: Strategy & Team Assembly
1.  **User Input:** "Assess the feasibility of building a vertical garden skyscraper in a tropical climate."
2.  **Orchestrator Analysis:** Analyzes keywords: *building, skyscraper, tropical climate*.
3.  **Team Proposal:** Orchestrator proposes:
    *   *Structural Engineer* (Focus: Load bearing, wind resistance)
    *   *Botanist/Landscape Architect* (Focus: Plant viability, irrigation)
    *   *Financial Analyst* (Focus: ROI, construction costs)
    *   *Skeptic/Risk Assessor* (Focus: General risk, tropical weather hazards)
4.  **HITL Checkpoint:** User approves the team.
    *   *User Action:* "Add a *Sustainability Expert* to check carbon footprint." -> Orchestrator adds to manifest.

### Phase 2: Domain-Specific Research
*   **Action:** The Agent Factory instantiates the approved agents.
*   **Execution:** Agents conduct initial research. The Botanist outputs specific irrigation needs; the Structural Engineer outputs material constraints.

### Phase 3: Cross-Pollination (The "Roundtable")
The Orchestrator manages the flow of information based on relevance, not just broadcasting to everyone.
1.  **Routing:**
    *   The **Structural Engineer's** report on "heavy water tanks" is routed specifically to the **Financial Analyst** (cost implication) and the **Botanist** (water availability).
    *   The **Financial Analyst** alerts the team about budget overruns.
2.  **Consensus/Conflict Detection:**
    *   The Orchestrator identifies if agents disagree (e.g., Botanist wants more water, Structural Engineer says it's too heavy).
    *   Orchestrator: *"Conflict detected. Requesting resolution plan from Structural Engineer."*

### Phase 4: Synthesis & Report
*   Orchestrator synthesizes the resolved perspectives into the final Markdown report.

## 5. Technical Implementation Details

### 5.1 Dynamic Prompt Generation (prompts/templates.py)
The system will use Jinja2 or F-string templates to generate system prompts on the fly.

```python
# Example of dynamic system prompt generation
def generate_system_prompt(role_config):
    return f"""
    You are a {role_config['role']} specializing in {role_config['domain']}.
    Your specific task for this project is: {role_config['goal']}.
    
    When reviewing the work of others, critique it ONLY from your perspective.
    Do not generalize. Stick to your expertise.
    """
```

### 5.2 Orchestrator Prompt Update
The Orchestrator needs a meta-prompt to understand domains.

```text
You are an expert Project Manager. Analyze the following topic:
"{user_topic}"

Determine the domain (e.g., Software, Construction, Economics, Policy).
Identify 3-5 distinct expert roles required to fully assess this topic from multiple angles.
Include at least one "Skeptic" or "Risk Analyst" type role.

Output a JSON list of roles and their specific goals.
```

### 5.3 Graph State Definition (LangGraph)
```python
from typing import TypedDict, List, Annotated

class AgentState(TypedDict):
    topic: str
    team_manifest: list[dict]  # Dynamic list of agents
    research_artifacts: dict    # Key: Agent Role, Value: Output
    debate_history: list
    consensus_achieved: bool
    final_report: str
```

## 6. Effort Assessment & Feasibility

### 6.1 Revised Effort Estimation
*   **Core Logic (Days 1-3):** Setup LangGraph, implement the "Strategist" node that outputs the JSON manifest.
*   **Agent Factory (Days 4-5):** Build the logic to read JSON and dynamically create LangGraph nodes/agents. This is the most complex part technically.
*   **Cross-Pollination Logic (Day 6):** Implementing the routing logic (e.g., "Pass Financial Output to Architect").
*   **CLI & HITL (Day 7):** Integrating the `questionary` library for interactive selection of the proposed team.

### 6.2 Feasibility & Risks
*   **Risk: Agent Hallucination of Expertise.** An LLM acting as a "Plumber" might give generic advice rather than technical plumbing advice.
    *   *Mitigation:* Use RAG (Retrieval Augmented Generation). If the Orchestrator spawns a "Plumber," it should ideally attach a tool to search plumbing codes/building regulations.
    *   *MVP Approach:* Rely on the base model's internal knowledge but enforce strict "Stay in Character" prompts.
*   **Risk: Token Explosion.** More agents = more context.
    *   *Mitigation:* The Orchestrator must summarize intermediate outputs. The Plumber doesn't need to read the Architect's full 10-page report; they only need a summary of the "Plumbing-relevant" sections.

## 7. Execution Plan

### Phase 1: The "Strategist" (Immediate)
*   Build the CLI loop that takes a topic.
*   Send the topic to a high-capability LLM (Orchestrator).
*   Ask it to return a JSON list of 4 roles.
*   Print this list to the terminal.

### Phase 2: The "Factory"
*   Implement the Agent Factory. Take the JSON list and create a loop that spins up generic Agent classes, injecting the specific system prompts generated in Phase 1.

### Phase 3: The "Roundtable"
*   Implement the graph loop.
*   Run agents in parallel for research.
*   Run agents sequentially for critique (passing relevant context).

### Phase 4: The Output
*   Final aggregation and Markdown export.

## 8. Sample Scenario: Economic Policy
**Input:** "Should the government implement a universal basic income?"
**Orchestrator Proposes:**
1.  *Labor Economist:* Focus on employment incentives.
2.  *Public Policy Analyst:* Focus on implementation logistics.
3.  *Fiscal Conservative:* Focus on inflation and budget deficits.
4.  *Social Advocate:* Focus on poverty reduction metrics.

**Process:** The Fiscal Conservative critiques the Social Advocate's cost estimates. The Labor Economist critiques the Fiscal Conservative's assumptions on workforce participation. The Orchestrator synthesizes these conflicts into a balanced "Feasibility Report."
