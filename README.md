# PiERN: Token-Level Routing for Integrating High-Precision Computation and Reasoning

Implementation of PiERN (Physically-isolated Experts Routing Network), submitted to ICML 2026.

## Overview

PiERN enables token-level dynamic switching between LLM language reasoning and high-precision scientific computation experts within a single Chain-of-Thought.

## Architecture

- **Physically-isolated Experts**: Pre-trained domain-specific models (e.g., FNO for PDEs), frozen after training
- **Text-to-Computation Module**: LLM-based decoder mapping natural language to expert numerical inputs
- **Token Router**: Lightweight classifier deciding at each token step whether to call LLM or an expert

## Project Structure

```
piern-rl/
├── src/
│   └── piern_rl/
│       ├── models/      # Expert models, router, text2comp
│       ├── training/    # Three-stage training pipeline
│       ├── data/        # Data loaders
│       └── utils/
├── tests/
├── configs/             # YAML configs
├── scripts/             # Training & eval scripts
└── data/                # Datasets (not tracked)
    ├── pdebench/
    ├── gcam/
    └── bms/
```

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Training

Three-stage training pipeline:

```bash
# Stage 1: Train expert models
python scripts/train_expert.py --config configs/expert.yaml

# Stage 2: Train text-to-computation module
python scripts/train_text2comp.py --config configs/text2comp.yaml

# Stage 3: Train token router
python scripts/train_router.py --config configs/router.yaml
```
