# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run all tests
pytest tests/

# Run a single test
pytest tests/test_router.py::test_routing_accuracy -v

# Lint
ruff check src/ tests/
```

## Architecture

PiERN implements token-level routing between an LLM and high-precision scientific computation experts within a single Chain-of-Thought. The system is built around three decoupled components trained in sequence.

### Three-Stage Training Pipeline

**Stage 1 — Expert Pretraining** (`src/piern_rl/models/experts.py`)
- Domain-specific models (e.g., FNO for PDE solving, neural nets for battery SoH) trained independently on task data
- Parameters are **frozen** after this stage; experts are never fine-tuned jointly
- Non-neural experts (e.g., linear profit calculators) skip this stage entirely

**Stage 2 — Text-to-Computation Module** (`src/piern_rl/models/text2comp.py`)
- A small LLM (Qwen3-0.6B) decoder trained to map natural language context → numerical expert inputs
- Loss: MSE + optional CLIP-inspired contrastive loss (`λ` controls the balance)
- Must learn semantic transformations: e.g., "subtract 0.1" → apply offset to input tensor

**Stage 3 — Token Router** (`src/piern_rl/models/router.py`)
- Lightweight classifier over LLM hidden states at each time step
- Binary (single expert) or multi-class (multiple experts + LLM) cross-entropy loss
- Monitors hidden state `h_t` and outputs routing probability `p(e | h_t)`

### Inference Flow

```
LLM generates text tokens  →  Router detects computation trigger  →
Text2Comp converts context to expert input  →  Expert runs high-precision computation  →
Result appended to context  →  LLM resumes generation
```

The LLM's language generation is **frozen** during expert calls; expert outputs are injected back into the token stream as context.

### Experiment Tasks

Three benchmark tasks live under `data/` and have corresponding configs in `configs/`:

| Task | Directory | Expert type |
|------|-----------|-------------|
| PDEBench (FNO) | `data/pdebench/` | Neural (FNO, frozen) |
| GCAM climate policy | `data/gcam/` | 9 domain experts |
| BMS battery management | `data/bms/` | Neural SoH + linear profit |

PDEBench uses 100 language templates (80 train / 20 zero-shot test) with Identity/Scaling/Offset perturbation strategies to test generalization of the Text-to-Computation module.

### Key Design Constraints

- Experts are **physically isolated**: they never share gradients with the LLM backbone
- The base LLM's weights are frozen throughout Stages 2 and 3 (only router and text2comp are trained)
- MMLU/GLUE performance must not degrade after training — monitor this during Stage 3
- Token budget: PiERN targets ~20 tokens per expert call vs. 500–1500 for multi-agent baselines
