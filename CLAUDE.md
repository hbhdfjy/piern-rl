# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_rl_training/test_reward.py -v

# Lint
ruff check .
```

## Project Structure

Two independent sub-projects share a common core (`piern_core/`):

### `piern_core/` — Shared Foundation
Contains the three PiERN components used by both sub-projects:
- `models/experts.py` — physically-isolated expert models (FNO, SoH network, linear calculators); always frozen after Stage 1
- `models/text2comp.py` — Qwen3-0.6B decoder fine-tuned to map natural language → expert numerical input tensors
- `models/router.py` — lightweight classifier over LLM hidden states `h_t`; outputs `p(e | h_t)` over expert set E

### Sub-project 1: `data_synthesis/` — Automated Data Synthesis & Augmentation
Builds training data for all three PiERN supervised training stages without manual annotation.

Key design:
- `generators/` produces (text, numerical tensor) pairs per task using language templates
- `augmenters/` applies the three perturbation strategies: Identity, Scaling (`x' = x·k`), Offset (`x' = x + b`)
- `validators/` filters out low-quality samples (MSE outliers, dimension mismatches)
- `pipeline/` orchestrates the full synthesis → augment → validate → export flow

### Sub-project 2: `rl_training/` — Multi-Turn Reinforcement Learning
Treats PiERN inference as an MDP and trains the Router + Text2Comp via GRPO (Stage 4, after supervised Stage 3).

Key design:
- `env/` wraps the full PiERN inference loop as a gym-style environment; state = (token context, hidden state, call history); action = {continue LLM | call expert e_i with input x}
- `reward/` implements per-task reward functions: RMSE-based for PDEBench, profit formula for BMS, policy alignment for GCAM
- `algorithms/` contains GRPO (primary), PPO, and REINFORCE; GRPO is preferred as it avoids a separate critic network
- `trainer/` runs the rollout → reward → update loop with KL constraint against the reference LLM to prevent language degradation

## Architecture Constraints

- Expert models are **always frozen** — never receive gradients from either sub-project
- The base LLM backbone is frozen during data synthesis; during RL it receives only LoRA updates
- RL is Stage 4 and requires a Stage 3 checkpoint as initialization — do not run RL from scratch
- MMLU/GLUE scores must be monitored during RL training to catch language degradation early

## Experiment Tasks

| Task | Data path | Experts | Reward signal |
|------|-----------|---------|---------------|
| PDEBench | `data/pdebench/` | 3 FNO models (one per PDE) | RMSE vs ground truth |
| GCAM | `data/gcam/` | 9 domain neural agents | Policy alignment score |
| BMS | `data/bms/` | SoH network + linear profit formula | `R = Δp·P - α·c_a·1200` |

BMS is the recommended starting point for RL validation: two-step call chain (SoH → profit), clear numerical reward, small dataset.
