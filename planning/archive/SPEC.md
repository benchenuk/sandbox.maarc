# MAARC: Iterative Multi-Agent Research Engine

## Project Overview

**Project Name**: MAARC
**Project Type**: Terminal-based (CLI) Python Application
**Core Functionality**: An orchestrated multi-agent system that conducts deep research through iterative debate and cross-examination between agents. It features a feedback loop architecture rather than linear execution, Human-in-the-Loop (HITL) checkpoints, and model-agnostic routing.
**Target Users**: System Architects, Technical Researchers, Project Planners, and Technical Decision Makers

---

## Technical Architecture & Framework Recommendation

### Framework Selection

#### Primary Recommendation: LangGraph (by LangChain)

While LlamaAgents and CrewAI are excellent frameworks, the specific requirement for "feeding relevant perspectives from one Agent to others... repeating until consensus" describes a **cyclic state machine**, not just a linear chain. LangGraph specifically excels at:

- **Cycles**: Native support for loops and feedback mechanisms
- **Persistence**: Memory between workflow steps
- **Fine-grained State Management**: Complete control over agent-to-agent message passing
- **Checkpointing**: Built-in support for resuming interrupted workflows

#### Alternative Options Considered

| Framework | Pros | Cons | Best For |
|-----------|------|------|----------|
| **LangGraph** | Full control over cycles, persistence, state | Steeper learning curve | Complex debate/consensus workflows |
| **CrewAI** | Fast setup, hierarchical structure | Limited cycle support, less flexible | Simple manager-worker patterns |
| **LlamaAgents** | Good tool integration | Less documented for cycles | Tool-heavy research |
| **AutoGen** | Microsoft-backed, flexible | Complex setup | Enterprise scenarios |

#### Recommended Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Orchestration** | LangGraph | State management & workflow cycles |
| **Model Abstraction** | LiteLLM | Unified API for OpenAI, Anthropic, Ollama, etc. |
| **CLI Interface** | Rich + Typer | Beautiful formatting, spinners, command handling |
| **Data Validation** | Pydantic | Schema validation for agent outputs |
| **Configuration** | YAML/JSON | Flexible model and agent configuration |

---

## UI/UX Specification

### Interface Structure

The CLI interface utilizes the Rich library for a sophisticated terminal experience.

#### 1. Initialization Phase

- **Command**: `python consensus.py start --topic "Scalable Microservices Arch"`
- **Visual Display**: ASCII Art Logo, System health checks (API keys presence)
- **Startup Sequence**: Validate configuration, check model endpoints, initialize agent pool

#### 2. Configuration Wizard (Interactive)

The system prompts for key parameters:

```
? Select Complexity Level: [Quick / Deep / Exhaustive]
  - Quick: 2-3 iteration cycles, basic agents
  - Deep: 5-7 cycles, full agent pool
  - Exhaustive: Unlimited cycles, all agents active

? Enable Human-in-the-Loop? [Y/N]
  - Y: Pause at checkpoints for user feedback
  - N: Auto-continue with default resolutions

? Select Primary Model: [GPT-4o / Claude-3.5-Sonnet / Local-Llama3 / Custom]
  - Models can be configured per-agent in config file
```

#### 3. The "War Room" (Runtime View)

During execution, the interface displays:

- **Header Bar**: Current Topic | Iteration # | Status (e.g., "Debating", "Consensus", "Paused")
- **Split Log Stream**:
  - Orchestrator (White): "Directing Agent A to review Agent B's finding..."
  - Researcher (Blue): "Gathering information on architecture patterns..."
  - Critic (Red): "Identifying potential bottleneck in proposed design..."
  - Architect (Green): "Synthesizing findings into solution v2..."
- **Status Indicators**: Animated spinners for active agents, color-coded output

#### 4. Human-in-the-Loop Checkpoints

When HITL is enabled, the system:

1. Pauses the workflow at defined checkpoints
2. Displays the current conflict or decision point
3. Presents options or accepts free-form input
4. Integrates user feedback into the next iteration

Example checkpoint:

```
══════════════════════════════════════════════════════════════
⚠️  HUMAN INTERVENTION REQUIRED
══════════════════════════════════════════════════════════════

The agents have reached a conflict on [Database Choice]:
  - Agent A argues for: PostgreSQL (ACID compliance)
  - Agent B argues for: MongoDB (flexible schema)

Options:
  [1] Accept Agent A's recommendation
  [2] Accept Agent B's recommendation
  [3] Request more analysis on both
  [4] Provide custom guidance

> Your choice: _
```

### Visual Style

| Element | Style |
|---------|-------|
| **Color Palette** | System: Slate Grey/White, Success: Emerald Green, Warning: Amber, Critical: Red |
| **Typography** | Monospace (Terminal default), Bold for Headers |
| **Layout** | Single-pane with collapsible sections, progress bars for long operations |
| **Icons** | ASCII-based status indicators (✓, ✗, ⚠, →, ◐) |

---

## Functionality Specification

### 1. Agent Roles & Definitions

The system dynamically spawns agents based on the research topic. Base agent templates include:

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Orchestrator** | Root Node | Maintains global state, decides consensus status, manages workflow |
| **Researcher** | Information Gathering | Gathers facts, searches knowledge bases, documents findings |
| **Critic** | Devil's Advocate | Finds flaws, challenges assumptions, identifies gaps |
| **Architect** | Synthesizer | Combines facts and critiques into coherent设计方案 |
| **Estimator** | Effort Analysis | Analyzes complexity, estimates efforts, identifies risks |

### 2. The Core Workflow (The "Debate Graph")

The execution follows a cyclic state machine:

```
┌─────────────────────────────────────────────────────────────────┐
│                      RESEARCH WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐      │
│  │  INPUT   │───▶│    PLAN     │───▶│  HITL CHECKPOINT │      │
│  │  TOPIC   │    │   PHASE     │    │   (User Approves) │      │
│  └──────────┘    └──────────────┘    └────────┬─────────┘      │
│                                                │                │
│                     ┌──────────────────────────▼                │
│                     │                                          │
│  ┌──────────┐      │    ┌──────────────────────────────┐     │
│  │  FINAL   │◀─────┼────│      EXECUTION LOOP          │     │
│  │  REPORT  │      │    │                              │     │
│  └──────────┘      │    │  ┌────────┐    ┌────────┐   │     │
│                    │    │  │ DRAFT  │───▶│CRITIQUE│───┼─────┘
│                    │    │  │ Phase  │    │ Phase  │   │ (Loop
│                    │    │  └────────┘    └────────┘   │  back)
│                    │    │       │              │        │     │
│                    │    │       ▼              ▼        │     │
│                    │    │  ┌────────────────────────────────┐  │
│                    │    │  │      REFINEMENT PHASE        │  │
│                    │    │  │  (Architect synthesizes)      │  │
│                    │    │  └────────────────┬───────────────┘  │
│                    │    │                   │                 │
│                    │    │                   ▼                 │
│                    │    │  ┌────────────────────────────────┐  │
│                    │    │  │     EVALUATION NODE           │  │
│                    │    │  │  (Orchestrator scores state)  │  │
│                    │    │  └───────────────┬────────────────┘  │
│                    │    │                   │                 │
│                    │    └───────────────────┼─────────────────┘  │
│                    │                        │                   │
│                    │              ┌─────────▼─────────┐         │
│                    │              │  CONSENSUS REACHED?│        │
│                    │              └─────────┬─────────┘         │
│                    │                        │                   │
│                    │              Yes       │      No          │
│                    │                │        │      │           │
│                    │                ▼        ▼      │           │
│                    │         ┌──────────┐    │       │         │
│                    └────────▶│  REPORT  │◀────┘       │         │
│                             │  PHASE   │──────────────┘         │
│                             └──────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Detailed Phase Descriptions

**Phase 1: Input Node**
- User defines the Problem Statement
- Optional: Context documents, existing research

**Phase 2: Plan Node**
- Orchestrator generates a research plan
- Defines which agents to spawn
- Sets iteration thresholds
- *HITL Checkpoint 1*: User approves/modifies the plan

**Phase 3: Execution Loop (Cyclic)**

| Step | Agent | Action | Output |
|------|-------|--------|--------|
| Step A | Researcher | Generates initial assessment | Draft findings |
| Step B | Critic | Reviews Step A, identifies flaws | Critique report |
| Step C | Architect | Updates design based on Step B | Refined proposal |
| Step D | Estimator | Analyzes effort and risks | Effort assessment |
| Step E | Orchestrator | Evaluates consensus score | Continue/Stop decision |

**Phase 4: Reporting Node**
- Formats final state into Markdown
- Includes debate summary, design specs, effort estimates

### 3. Model Provider Abstraction

Using LiteLLM, the system creates a unified completion interface:

```python
# Example model configuration (models.yaml)
models:
  orchestrator:
    provider: openai
    model: gpt-4o
    temperature: 0.7

  researcher:
    provider: anthropic
    model: claude-3-sonnet-20240229
    temperature: 0.5

  critic:
    provider: openai
    model: gpt-4-turbo
    temperature: 0.9  # Higher for creative critique

  architect:
    provider: openai
    model: gpt-4o
    temperature: 0.3  # Lower for precise synthesis

  local_backup:
    provider: ollama
    model: llama3
    api_base: http://localhost:11434
```

### 4. Consensus Detection

The orchestrator evaluates consensus using multiple criteria:

| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| **Agreement Score** | > 0.85 | Ratio of agents supporting the conclusion |
| **Conflict Count** | < 2 | Number of unresolved conflicts |
| **Iteration Count** | >= Min iterations | Minimum debate cycles completed |
| **Stability Score** | > 0.9 | Similarity between last 2 iterations |

### 5. Output Generation

**Format**: Markdown (`.md`)
**Default Location**: `/reports/` directory

**Report Structure**:

```markdown
# Research Report: [Topic]

## Executive Summary
[High-level feasibility and key findings]

## Research Process
- Topic: [Original question]
- Duration: [Time taken]
- Iterations: [Number of cycles]
- Agents Used: [List of active agents]

## The Debate
### Key Conflicts
- [Conflict 1]: [Resolution]
- [Conflict 2]: [Resolution]

### Perspectives
- [Agent Name]: [Their position and reasoning]

## System Design
### Architecture
[Technical specification]

### Components
[Detailed component breakdown]

## Effort Estimation
### T-Shift Sizing
- XS / S / M / L / XL / XXL

### Risk Assessment
[Identified risks and mitigations]

## Action Plan
### Phase 1: [Timeline]
- [Task 1]
- [Task 2]

### Phase 2: [Timeline]
- [Task 3]
- [Task 4]

## Appendix
### Configuration Used
[Model settings, agent configs]

### Raw Agent Outputs
[Full transcripts if requested]
```

---

## Extensibility Plan

### Phase 1: MVP (Current)
- CLI interface with basic agent pool
- Sequential debate workflow
- Simple consensus detection
- Markdown export

### Phase 2: Tool Integration (Q2)
- Web search integration (Tavily, SerpAPI)
- Code analysis tools
- Document upload support

### Phase 3: Memory & Persistence (Q3)
- ChromaDB for long-term memory
- Session persistence (resume interrupted research)
- Historical analysis

### Phase 4: Web UI (Q4)
- FastAPI backend
- React frontend
- Real-time collaboration

---

## Configuration File Format

### `config.yaml`

```yaml
app:
  name: MAARC
  version: 0.1.0

research:
  default_iterations: 5
  min_iterations: 3
  max_iterations: 10
  consensus_threshold: 0.85

models:
  default_provider: openai
  fallback_to_local: true

  # Per-agent model assignment
  agents:
    orchestrator:
      provider: openai
      model: gpt-4o
    researcher:
      provider: anthropic
      model: claude-3-sonnet-20240229
    critic:
      provider: openai
      model: gpt-4-turbo
    architect:
      provider: openai
      model: gpt-4o
    estimator:
      provider: anthropic
      model: claude-3-haiku-20240229

output:
  format: markdown
  directory: reports
  include_raw_transcripts: false

human_in_the_loop:
  enabled: true
  checkpoint_frequency: every_cycle  # every_cycle, end_only, manual
  pause_on_conflicts: true
```

---

## Acceptance Criteria

### Functional Requirements

| ID | Requirement | Success Condition |
|----|-------------|-------------------|
| F1 | CLI Application Launch | `python main.py --help` displays help menu |
| F2 | Topic Input | System accepts topic and generates research plan |
| F3 | Agent Spawning | At least 3 distinct agent personas are active |
| F4 | Debate Loop | Logs show data passing: Agent A → Agent B → Agent A |
| F5 | HITL Checkpoints | System pauses and accepts user input at checkpoints |
| F6 | Consensus Detection | System automatically proceeds when consensus reached |
| F7 | Markdown Export | Valid `.md` file generated in reports directory |
| F8 | Model Routing | Different agents can use different model providers |

### Non-Functional Requirements

| ID | Requirement | Success Condition |
|----|-------------|-------------------|
| NF1 | Startup Time | Application initializes in < 3 seconds |
| NF2 | Error Handling | Graceful degradation when API keys missing |
| NF3 | Extensibility | New agents can be added without modifying core |
| NF4 | Configuration | All settings externalized to config files |

### Test Scenarios

**Test 1: Basic Research Flow**
```bash
python main.py start --topic "Design a REST API for a todo app"
```
- Expected: System generates research, produces report

**Test 2: HITL Intervention**
```bash
python main.py start --topic "Database selection for e-commerce" --hitl
```
- Expected: System pauses, accepts input, integrates feedback

**Test 3: Consensus Detection**
```bash
python main.py start --topic "Simple static website hosting"
```
- Expected: Few iterations, quick consensus on simple topic

**Test 4: Model Routing**
```bash
# Configure critic to use local Ollama
python main.py start --topic "Microservices patterns" --config custom.yaml
```
- Expected: Logs show different endpoints for different agents

---

## File Structure

```
MAARC/
├── main.py                 # Entry point
├── pyproject.toml          # Project configuration
├── config.yaml             # Default configuration
├── requirements.txt        # Dependencies
├── README.md               # Documentation
├── consensus/
│   ├── __init__.py
│   ├── cli.py              # CLI interface (Typer)
│   ├── ui.py               # Rich UI components
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py         # Base agent class
│   │   ├── orchestrator.py
│   │   ├── researcher.py
│   │   ├── critic.py
│   │   ├── architect.py
│   │   └── estimator.py
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── state.py        # State definitions
│   │   ├── nodes.py        # Graph nodes
│   │   └── graph.py        # LangGraph setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── lite_llm_client.py
│   │   └── providers.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py       # Configuration loader
│       └── markdown.py     # Report generator
└── reports/                # Output directory (generated)
```

---

## Implementation Notes

### Key Design Decisions

1. **LangGraph over CrewAI**: Chosen because the iterative debate workflow requires cycles, not just linear chains. LangGraph provides explicit cycle support.

2. **LiteLLM for Model Abstraction**: Enables easy swapping of model providers without code changes. Critical for cost optimization and fallback handling.

3. **Rich + Typer**: Rich provides the visual polish needed for a professional CLI tool. Typer offers clean command-line argument handling with automatic help generation.

4. **Pydantic for State**: Agent states and messages are validated using Pydantic models, ensuring type safety and clear interfaces.

5. **YAML Configuration**: User-accessible configuration file allows customization without code changes. Supports both quick-start defaults and advanced per-agent routing.

### Future Considerations

- **Agent Specialization**: Add domain-specific agents (Security Expert, Performance Engineer)
- **Tool Integration**: Give agents access to web search, code execution, documentation lookup
- **Multi-modal Output**: Support for HTML, PDF, and presentation export
- **Collaboration**: Multi-user research sessions with shared context
