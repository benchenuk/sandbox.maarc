# System Design Report: AI Multi-Agent Researcher (MVP) - Revision 3

## 1. Executive Summary
This design iteration refines the system for efficiency and scalability. It confirms the use of **LangGraph** for its native support of parallel agent execution (fan-out/fan-in), ensuring rapid research synthesis. The development roadmap is restructured into iterative "Vertical Slices," allowing for a functional MVP loop before adding complexity. The design is illustrated using a scenario analyzing the challenges of the Japanese economy.

## 2. Technical Architecture: Parallel Dispatch

### 2.1 Parallel Execution in LangGraph
**Yes, LangGraph fully supports parallel dispatch.**
The Orchestrator node can return a list of next nodes to invoke, effectively "fan-out" the workflow. The graph will automatically execute these agent nodes in parallel threads. Once all parallel nodes complete, the graph can "fan-in" to a synchronization node (e.g., the Consensus Check).

### 2.2 State Management for Parallelism
When agents run in parallel, they write to the shared `AgentState` simultaneously. To prevent data races or overwrites:
*   **Research Artifacts:** We will use a list of dictionaries or a merged dictionary in the state definition.
*   **LangGraph `reduce` function:** The state will be configured to merge outputs. If Agent A writes `{ economist: "..." }` and Agent B writes `{ sociologist: "..." }` simultaneously, the state merges them into a single artifact map.

## 3. Workflow Design (Refined)

*   **Phase 1: Strategy:** Orchestrator plans the team.
*   **Phase 2: Parallel Research (Fan-Out):**
    *   Orchestrator spawns `N` agents (Economist, Government, Geopolitics, Society).
    *   **All agents run simultaneously** to gather initial perspectives.
    *   **Fan-In:** Results are collected and merged into the `research_artifacts` state.
*   **Phase 3: Iterative Debate:**
    *   Orchestrator reviews merged artifacts.
    *   Identifies conflicts (e.g., Economists want inflation; Government agent fears public backlash).
    *   Routes specific critiques to relevant agents (Sequential or Parallel depending on need).
*   **Phase 4: Synthesis:** Final report generation.

## 4. Sample Scenario: "What are the challenges of the Japanese economy?"

This scenario demonstrates the dynamic role assignment and perspective collision.

### Step 1: Strategy & Team Assembly
*   **Input:** "What are the challenges of the Japanese economy?"
*   **Orchestrator Analysis:** Identifies domain: *Macroeconomics / Geopolitics / Sociology*.
*   **Proposed Team:**
    1.  **Labor Economist:** Focus on aging population, shrinking workforce.
    2.  **Monetary Policy Analyst:** Focus on BOJ policies, yen valuation, deflation.
    3.  **Geopolitical Strategist:** Focus on regional security, China relations, energy reliance.
    4.  **Sociologist:** Focus on rigid work culture, gender gap, immigration resistance.
*   **HITL:** User approves team.

### Step 2: Parallel Research (The Fan-Out)
The Orchestrator dispatches all four agents simultaneously.

*   **Agent A (Economist):** Returns analysis on debt-to-GDP ratio and labor shortage. Suggests increasing immigration.
*   **Agent B (Monetary Policy):** Returns analysis on the struggle to exit yield curve control. Notes weak yen impact.
*   **Agent C (Geopolitics):** Highlights reliance on imported energy and semiconductor supply chains.
*   **Agent D (Sociologist):** Identifies cultural barriers to rapid immigration and low productivity in traditional sectors.

### Step 3: Cross-Pollination & Consensus
The Orchestrator detects a critical intersection:
*   **Conflict:** The Economist suggests "Mass Immigration" to solve labor shortage.
*   **Rebuttal (from Sociologist):** "Japanese society currently lacks the social infrastructure for mass integration, risking social friction."
*   **Rebuttal (from Government/Policymaker perspective):** "Immigration reform is politically sensitive and slow-moving."

The Orchestrator feeds the Sociologist's critique back to the Economist for revision.
*   **Revised Consensus:** The Economist updates the recommendation to "Gradual, specialized immigration coupled with automation investment."

### Step 4: Final Output
A Markdown report synthesizing these intersecting views, highlighting that the economic challenges are inseparable from social and geopolitical constraints.

## 5. Execution Plan: Iterative MVP Approach

We will build the system in vertical slices. Each iteration produces a usable tool, just with increasing intelligence.

### Iteration 1: The "Dumb" Loop (The Skeleton)
*   **Goal:** Prove the graph works and agents can talk.
*   **Implementation:**
    *   Hardcode a generic prompt: "You are a helpful assistant."
    *   Hardcode 2 Agents: Agent A writes a paragraph. Agent B critiques it.
    *   **Loop:** Agent A -> Agent B -> Agent A (Revises) -> End.
    *   **Tech:** LangGraph setup, basic CLI print.
*   **Outcome:** A functioning CLI loop where two generic agents pass text back and forth.

### Iteration 2: Dynamic Strategy (The Brain)
*   **Goal:** Implement the "Orchestrator" to create roles dynamically.
*   **Implementation:**
    *   Add the "Strategy Node" before the agents.
    *   Input: "Analyze Japanese Economy."
    *   Orchestrator (GPT-4) generates JSON manifest: `[Labor Economist, Sociologist]`.
    *   **Factory:** Read JSON -> Create Agent A and Agent B with specialized system prompts.
*   **Outcome:** The app now creates *relevant* agents based on the topic, but they still run sequentially.

### Iteration 3: Parallel Execution & Synthesis (The Engine)
*   **Goal:** Speed and aggregation.
*   **Implementation:**
    *   Convert sequential execution to **Parallel (Fan-out)**.
    *   Add the `reduce` logic to merge parallel outputs.
    *   Add a "Synthesizer" node at the end to merge findings into Markdown.
*   **Outcome:** A fast research tool that generates a report from multiple parallel perspectives.

### Iteration 4: Debate & Human-in-the-Loop (The Polish)
*   **Goal:** Refinement and Control.
*   **Implementation:**
    *   Add the "Consensus Check" loop (Step 3 in Workflow).
    *   Implement `interrupt_before` in LangGraph for Human approval of the team.
    *   Add Markdown file export.
*   **Outcome:** The full MVP described in this design.

## 6. Conclusion
This design now explicitly handles the complexity of parallel execution to optimize performance and utilizes a concrete scenario to demonstrate the power of perspective-taking. By starting with a hardcoded "Dumb Loop" in Iteration 1, we mitigate risk and ensure the core infrastructure is solid before adding the complexity of dynamic agent generation.
