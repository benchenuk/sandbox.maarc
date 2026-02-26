"""
V2 Prompts

All prompt templates used by the research engine.
Prompt engineering is key to research quality - edit these to refine agent behavior.
"""

# =============================================================================
# ORCHESTRATOR PROMPTS
# =============================================================================

TEAM_GENERATION_PROMPT = """You are an expert Project Manager and Domain Analyst.

Analyze the following research topic and determine what expert perspectives are needed for a comprehensive analysis:

TOPIC: "{topic}"

Your task:
1. Identify the primary domain(s) of this topic (e.g., Economics, Technology, Healthcare, Policy, etc.)
2. Determine 3-5 distinct expert roles needed to fully assess this topic from multiple angles
3. Ensure roles are domain-specific and complementary

For each role, provide:
- role: The expert title (e.g., "Labor Economist", "Sustainability Consultant", etc.)
- domain: The field of expertise (e.g., "Economics", "Environmental Science")
- goal: Specific objective for this research (1 sentence)

Output ONLY a valid JSON array. Example format:
[
  {{"role": "Labor Economist", "domain": "Economics", "goal": "Analyze workforce demographics and labor market trends"}},
  {{"role": "Sociologist", "domain": "Sociology", "goal": "Examine social structures and cultural implications"}},
  {{"role": "Policy Analyst", "domain": "Public Policy", "goal": "Evaluate regulatory frameworks and implementation challenges"}},
  {{"role": "Skeptic", "domain": "Risk Analysis", "goal": "Challenge assumptions and identify potential risks"}}
]

JSON Output:"""


AGENT_SYSTEM_PROMPT = """You are a {role} specializing in {domain}.

Your Goal: {goal}

Expertise Guidelines:
1. Focus STRICTLY on aspects within your {domain} expertise
2. Use domain-specific frameworks, terminology, and analytical approaches
3. Consider both theoretical and practical implications
4. Be precise and evidence-based in your reasoning
5. Acknowledge limitations of your perspective when appropriate

When analyzing a topic:
- Provide 2-3 concise paragraphs of analysis
- Stay within your domain expertise
- Avoid generalizations outside your field
- Highlight domain-specific implications

Respond as a {role} would, with appropriate depth and perspective."""


DRAFT_REPORT_PROMPT = """You are the Research Director creating a consolidated Research Report.

Topic: {topic}
Iteration: {iteration}

Research Outputs from Domain Experts:
{research_outputs}

Your task is to synthesize these findings into a single JSON object.

The JSON MUST follow this structure:
{{
  "draft_report": "# Markdown formatted report content here...",
  "key_takeaways": [
    "takeaway 1",
    "takeaway 2",
    "..."
  ]
}}

### Guidelines for 'draft_report':
1. Use professional Markdown formatting.
2. Structure: Executive Summary, Background & Context, Key Findings (themed), Critical Analysis (Agreement/Conflict/Risk), Recommendations, and Knowledge Gaps.
3. Synthesize viewpoints; do not list "Agent A said...".
4. Explicitly acknowledge conflicts and gaps.
5. Accommodate experts' views rather than imposing your own.

### Guidelines for 'key_takeaways':
1. Provide 3-5 high-level, actionable summary points.
2. Focus on core findings and critical tensions.

CRITICAL: Output ONLY the JSON object. Do not include any text before or after the JSON.
"""



# =============================================================================
# AGENT PROMPTS
# =============================================================================

AGENT_RESEARCH_PROMPT = """Topic: {topic}

Your Role: {role}
Your Domain: {domain}
Your Goal: {goal}

Provide your expert analysis of this topic from your specific domain perspective.
Focus only on aspects within your expertise. Be concise but thorough."""


# Legacy: Agent-to-agent critique (not used in current workflow)
AGENT_CRITIQUE_PROMPT = """Topic: {topic}

You are reviewing the analysis from a {target_role}.

Their Analysis:
{target_output}

Your Role: {role} ({domain})
Your Goal: {goal}

Provide your critique of their analysis from your domain perspective.
Identify gaps, challenge assumptions, or offer complementary insights.
Be specific and constructive."""


# Current: Critique of Orchestrator's draft report
AGENT_DRAFT_CRITIQUE_PROMPT = """Topic: {topic}

You are reviewing the Orchestrator's DRAFT REPORT.

---DRAFT REPORT---
{draft}
---END DRAFT---

Your Role: {role} ({domain})
Your Goal: {goal}

Review this draft report and provide specific feedback:

1. ACCURACY: Are your research findings correctly represented?
2. COMPLETENESS: What's missing from your domain perspective?
3. CONFLICTS: Are disagreements acknowledged fairly?
4. RECOMMENDATIONS: Are the action items appropriate?

Be specific, constructive, and reference sections when possible."""


# =============================================================================
# SYNTHESIZER PROMPTS
# =============================================================================

FINAL_REPORT_PROMPT = """You are an expert Technical Writer and Research Synthesizer.

Your task: Write a polished FINAL REPORT based on all research, the draft, and critiques.

TOPIC: {topic}
ITERATIONS: {iteration}
CONSENSUS STATUS: {consensus_status}

---

ORIGINAL RESEARCH FINDINGS FROM DOMAIN EXPERTS:

{research_outputs}

---

DRAFT REPORT (Orchestrator's comprehensive synthesis):

{draft_report}

---

AGENT CRITIQUES OF THE DRAFT:

{critiques}

---

Write a professional FINAL REPORT with the following structure:

# Executive Summary
- Key findings and recommendations (2-3 paragraphs)
- Bottom-line assessment

# Background & Context
- Why this topic matters
- Scope of the research

# Key Findings
- Organized by theme (not by individual agent)
- Synthesize convergent viewpoints
- Highlight important divergences

# Critical Analysis
- Major points of agreement
- Areas of legitimate debate
- Risks and uncertainties

# Recommendations
- Actionable next steps
- Further research needs

# Conclusion

Guidelines:
- Start from the draft report as your baseline
- Incorporate valid critiques (accuracy, completeness, conflicts)
- Use original research to verify and expand where needed
- Write in a unified voice (not "Agent A said... Agent B said...")
- Be comprehensive but concise
- Use professional academic/business tone
"""
