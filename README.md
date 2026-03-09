# PiERN: Token-Level Routing for Integrating High-Precision Computation and Reasoning

Implementation of PiERN (Physically-isolated Experts Routing Network), submitted to ICML 2026.

## Overview

PiERN enables token-level dynamic switching between LLM language reasoning and high-precision scientific computation experts within a single Chain-of-Thought.

This repository contains two sub-projects:

### 1. Automated Data Synthesis & Augmentation Pipeline (`data_synthesis/`)

Automatically constructs and augments training data for all three PiERN training stages:
- Language template generation for Text-to-Computation training
- Perturbation strategies: Identity / Scaling / Offset
- Token Router label construction from synthesized trajectories
- Validation and quality filtering

### 2. Multi-Turn Reinforcement Learning (`rl_training/`)

Extends PiERN's supervised routing (Stage 3) with RL-based policy optimization:
- GRPO-based training over the Router + Text2Comp modules
- Multi-turn expert call trajectories as rollouts
- Task-level reward signals (RMSE, profit, policy alignment)
- KL-constrained LLM backbone to preserve language ability

## Architecture

- **Physically-isolated Experts**: Pre-trained domain-specific models (FNO, SoH network, linear calculators), frozen after training
- **Text-to-Computation Module**: Qwen3-0.6B decoder mapping natural language → expert numerical inputs
- **Token Router**: Lightweight classifier over LLM hidden states deciding at each token step whether to call LLM or an expert

## Project Structure

```
piern/
├── piern_core/          # Shared: expert models, router, text2comp, base LLM wrapper
│   ├── models/
│   ├── data/
│   └── utils/
├── data_synthesis/      # Sub-project 1: automated data synthesis & augmentation
│   ├── pipeline/        # End-to-end synthesis pipeline orchestration
│   ├── generators/      # Template & trajectory generators per task
│   ├── augmenters/      # Perturbation strategies (identity/scaling/offset)
│   ├── validators/      # Quality filtering & consistency checks
│   └── utils/
├── rl_training/         # Sub-project 2: multi-turn RL
│   ├── algorithms/      # GRPO, PPO, REINFORCE implementations
│   ├── reward/          # Reward functions per task (RMSE, profit, etc.)
│   ├── env/             # PiERN rollout environment (MDP wrapper)
│   ├── trainer/         # RL training loop
│   └── utils/
├── configs/
│   ├── data_synthesis/
│   └── rl_training/
├── scripts/
│   ├── data_synthesis/
│   └── rl_training/
├── tests/
│   ├── test_data_synthesis/
│   └── test_rl_training/
└── data/
    ├── pdebench/
    ├── gcam/
    └── bms/
```

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Experiment Tasks

| Task | Data | Expert type |
|------|------|-------------|
| PDEBench (FNO) | `data/pdebench/` | Neural (FNO, frozen) |
| GCAM climate policy | `data/gcam/` | 9 domain neural agents |
| BMS battery management | `data/bms/` | Neural SoH + linear profit |
