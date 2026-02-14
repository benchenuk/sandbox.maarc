# Design B.1: Hybrid Parallel-Squential Execution with Dynamic Teams

## Date: 2026-02-14

## Context

Iteration 3 initially implemented pure parallel execution where all agents (including Skeptics) ran concurrently using `asyncio.gather`. This created a fundamental issue: **Skeptics cannot critique research that hasn't been produced yet**.

## Problem Analysis

### The Exponential Complexity Trap

If every agent critiques every other agent's output:
- n agents → n×(n-1) critique relationships
- 5 agents → 20 critique connections
- Creates noise, not signal

### The Empty Critique Problem

Running Skeptics in parallel with researchers means:
- Skeptics have nothing to critique (research incomplete)
- They either critique assumptions (wasted effort) or wait (wasted parallelism)

## Proposed Solution: 4-Phase Iteration Loop

```
┌─────────────────────────────────────────────────────────┐
│  Phase 1: RESEARCH (Fan-Out)                            │
│    All agents conduct independent research in parallel  │
│    [Economist] ──┐                                      │
│    [Technologist]┼──→ Fan-in                            │
│    [Skeptic] ────┘     (Skeptic does initial research   │
│                         on risks, not critique yet)     │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 2: SYNTHESIS (Orchestrator)                      │
│    Orchestrator summarizes all findings:                │
│    - Key agreements                                     │
│    - Identified conflicts                               │
│    - Knowledge gaps                                     │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 3: CRITIQUE (Fan-Out)                            │
│    All agents critique THE SUMMARY (not each other)     │
│    - Common baseline for all critiques                  │
│    - O(n) complexity instead of O(n²)                   │
│    - Focused on synthesized understanding               │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 4: DECISION (Orchestrator)                       │
│    Evaluate:                                            │
│    - Consensus reached? → Final report                  │
│    - More research needed? → Assemble NEW team → Loop   │
└─────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Synthesis as the Critique Baseline

All agents critique the **orchestrator's summary**, not individual research outputs. This creates:
- Single source of truth for critiques
- Comparable critique perspectives
- Focus on "what we collectively know" not "what Alice said"

### 2. Dynamic Team Reassembly

Each iteration can have a different team composition:

```
Iteration 1: [Economist, Technologist, Generalist]
   ↓ Conflict on economic modeling
Iteration 2: [Labor Economist, Financial Analyst, Technologist]
   ↓ Tech consensus reached
Iteration 3: [Financial Analyst, Risk Specialist]  
```

Orchestrator decides team composition based on:
- Unresolved conflicts from previous round
- Knowledge gaps identified
- Expertise no longer needed

### 3. The Skeptic Role Reimagined

| Phase | Skeptic Activity |
|-------|------------------|
| Research | Investigates risks, edge cases, assumptions |
| Critique | Challenges the summary's completeness |

Skeptics are **permanent critique participants**, not just research agents.

## Benefits

| Aspect | Improvement |
|--------|-------------|
| Complexity | O(n) critiques vs O(n²) |
| Focus | Critiques reference common baseline |
| Adaptability | Teams evolve per iteration needs |
| Quality | Orchestrator summary gates next phase |

## Implementation Notes

- **Phase 1 & 3** use `asyncio.gather` for true parallelism
- **Phase 2 & 4** are orchestrator-only (sequential, blocking)
- Team manifest is regenerated between iterations if needed
- State carries forward: agent_outputs accumulate across iterations
