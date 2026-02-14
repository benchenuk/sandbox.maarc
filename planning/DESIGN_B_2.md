# Design B.2: Draft Report Pattern with Comprehensive Preservation

## Date: 2026-02-14

## Problem Statement

In Design B.1, the Orchestrator's synthesis was a **summary** - condensing agent outputs into key points. This caused:
1. **Information loss** - Rich details discarded
2. **Poor critique quality** - Agents critiqued summaries, not comprehensive drafts
3. **No early termination** - Couldn't assess if current iteration was "good enough"

## Solution: Draft Report Pattern

The Orchestrator now produces a **comprehensive draft report** (Option B) - a complete structured document that looks like the final report, just not polished.

## New 5-Phase Iteration Loop

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: RESEARCH (Fan-Out)                                │
│    All agents produce detailed research                      │
│    Output: Rich agent_outputs (preserved in state)           │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: DRAFT REPORT (Orchestrator)                       │
│    Creates comprehensive structured report:                  │
│    - Executive Summary                                       │
│    - Background & Context                                    │
│    - Key Findings (by theme, not by agent)                   │
│    - Critical Analysis (agreements, conflicts, risks)        │
│    - Recommendations                                         │
│    - Identified Gaps                                         │
│    Output: draft_report (comprehensive, not polished)        │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: CRITIQUE (Fan-Out)                                │
│    All agents critique THE DRAFT REPORT:                     │
│    - "Section 3 misrepresents my finding about X"            │
│    - "Missing critical risk Y in Analysis"                   │
│    - "Conflict Z needs explicit acknowledgment"              │
│    Output: draft_critiques                                   │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: EVALUATION (Orchestrator Decision)                │
│    Assesses:                                                 │
│    - Are critiques minor/polishing? → FINALIZE               │
│    - Are there substantive gaps? → LOOP (new team)           │
│    - Is consensus reached? → FINALIZE                        │
│    Decision: "finalize" or "continue"                        │
└────────────────────────┬────────────────────────────────────┘
                         ▼
                    ┌─────────────┐
           ┌───────│  finalize?  │────────┐
           │       └─────────────┘        │
           │ NO                           │ YES
           ▼                              ▼
┌────────────────────┐          ┌──────────────────────────────┐
│  LOOP BACK         │          │  Phase 5: FINAL REPORT       │
│  (new iteration)   │          │  (Synthesizer Agent)         │
│  - Keep all prior  │          │                              │
│    research in     │          │  Inputs:                     │
│    state           │          │  - All agent_outputs         │
│  - Optionally      │          │  - draft_report              │
│    reassemble team │          │  - draft_critiques           │
└────────────────────┘          │                              │
                                │  Output: Polished, unified   │
                                │  professional report         │
                                └──────────────────────────────┘
```

## Key Design Elements

### 1. Draft Report Structure (Option B)

The draft is a **complete report skeleton**, not a summary:

```markdown
# Draft Report: {topic}

## Executive Summary
[2-3 paragraphs - synthesized findings]

## Background & Context
[Why this matters, scope]

## Key Findings
### Theme 1: [e.g., Economic Impact]
[Synthesized from multiple agents]

### Theme 2: [e.g., Technical Feasibility]
...

## Critical Analysis
### Points of Agreement
### Areas of Debate
### Risk Assessment

## Recommendations
[Action items]

## Identified Gaps
[What we don't know yet]
```

### 2. Critique Quality Improvement

Instead of: *"Your summary missed my labor market point"*

Now: *"Section 3.2 'Economic Impact' understates the 18-month transition period I identified. Recommend adding: 'Organizations should plan for 18-month workforce adaptation.'"*

### 3. State Preservation

```python
ResearchState:
    agent_outputs: Dict[str, str]  # All research (accumulates across iterations)
    draft_report: str              # Current draft
    draft_critiques: Dict[str, str] # Critiques of current draft
    prior_drafts: List[str]        # History of drafts (optional)
```

### 4. Early Termination Criteria

Orchestrator can finalize when:
- Critiques are minor/polishing only (no substantive issues)
- All major conflicts acknowledged in draft
- No significant gaps identified
- Max iterations reached (fallback)

## Benefits

| Aspect | Improvement |
|--------|-------------|
| **Content Preservation** | Original research never lost |
| **Critique Quality** | Specific, actionable feedback on draft |
| **Early Termination** | Can stop when "good enough" |
| **Team Reassembly** | New teams see prior draft + gaps |
| **Final Quality** | Synthesizer has more context |

## Implementation Notes

- Draft report uses same LLM provider as orchestrator
- Lower temperature (0.3-0.5) for consistent structure
- Critiques target specific sections when possible
- Final Synthesizer can reference draft as "starting point"
