# Consensus-CLI

Iterative Multi-Agent Research Engine with debate-based consensus.

## Overview

Consensus-CLI is a terminal-based application that conducts deep research through iterative debate and cross-examination between AI agents. It features a feedback loop architecture, Human-in-the-Loop (HITL) checkpoints, and model-agnostic routing.

## Features

- **Multi-Agent Debate**: 5 specialized agents (Researcher, Critic, Architect, Estimator, Orchestrator)
- **Iterative Workflow**: Cyclic state machine using LangGraph
- **Human-in-the-Loop**: Pause and provide feedback at checkpoints
- **Multi-Model Support**: Works with OpenAI, Anthropic, Ollama via LiteLLM
- **Rich CLI UI**: Beautiful terminal interface with spinners and panels
- **Markdown Reports**: Generate comprehensive research reports

## Installation

```bash
# Clone or navigate to the project
cd consensus-cli

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Configuration

Edit `config.yaml` to customize:

- Model providers per agent
- Iteration counts
- Consensus thresholds
- HITL settings
- Output directory

```yaml
models:
  agents:
    orchestrator:
      provider: openai
      model: gpt-4o
    researcher:
      provider: openai
      model: gpt-4o
```

## Usage

### Set API Key

```bash
export OPENAI_API_KEY=your_key_here
# or
export ANTHROPIC_API_KEY=your_key_here
```

### Commands

```bash
# Show help
python main.py --help

# Start research
python main.py start --topic "Your research topic"

# With custom iterations
python main.py start -t "Database design" -i 5

# Enable Human-in-the-Loop
python main.py start -t "API design" --hitl

# Verbose output
python main.py start -t "Microservices" -v

# Show configuration
python main.py configure --show

# List agents
python main.py agents

# Show version
python main.py version
```

## Output

Reports are saved to the `reports/` directory as Markdown files.

## Requirements

- Python 3.11+
- OpenAI or Anthropic API key (or local Ollama)

See `SPEC.md` for detailed architecture documentation.
