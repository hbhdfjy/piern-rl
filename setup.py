from setuptools import setup, find_packages

setup(
    name="piern",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.40.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "neuraloperator>=0.3.0",
        "flopy>=3.7.0",
        "h5py>=3.8.0",
        "pandas>=2.0.0",
        "accelerate>=0.28.0",
        "peft>=0.10.0",
        "trl>=0.8.0",
        "wandb>=0.16.0",
        "pyyaml>=6.0",
        "omegaconf>=2.3.0",
        "tqdm>=4.65.0",
        "einops>=0.7.0",
    ],
    entry_points={
        "console_scripts": [
            "piern-modflow=data_synthesis.pipeline.modflow_pipeline:main",
        ],
    },
)
