#!/usr/bin/env python3
"""
Stage A: Generate all input files for parallel processing.
Creates N pickled input files and uploads them to storage (GCS or local).
"""

import os
import sys
import pickle
import argparse

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage
import numpy as np
import copy
from epydemix import EpiModel


def main():
    parser = argparse.ArgumentParser(
        description="Generate input files for batch processing"
    )
    parser.add_argument(
        "--count", type=int, required=True, help="Number of input files to generate"
    )
    parser.add_argument(
        "--seed", type=int, required=True, help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    # Get configuration
    config = storage.get_config()

    print(f"Starting Stage A: Generating {args.count} inputs")
    print(f"  Storage mode: {config['mode']}")
    print(f"  Dir prefix: {config['dir_prefix']}")
    print(f"  Sim ID: {config['sim_id']}")
    print(f"  Run ID: {config['run_id']}")
    print(f"  Seed: {args.seed}")
    if config['mode'] == 'cloud':
        print(f"  Bucket: {config['bucket']}")

    base_sir_model = EpiModel(
        name="SIR Model",
        compartments=["S", "I", "R"],  # Susceptible, Infected, Recovered
    )

    beta_list = np.linspace(0.1, 0.4, args.count)

    # Generate and upload input files
    for i in range(args.count):
        beta = beta_list[i]

        sir_model = copy.deepcopy(base_sir_model)
        sir_model.add_transition(
            source="S", target="I", params=(beta, "I"), kind="mediated"
        )
        sir_model.add_transition(source="I", target="R", params=0.1, kind="spontaneous")

        # Pickle the data
        data = pickle.dumps(sir_model)

        # Upload to storage (GCS or local)
        # Use storage.get_path() to build the path automatically
        path = storage.get_path("inputs", f"input_{i:04d}.pkl")
        storage.save_bytes(path, data)

        print(f"  Generated: {path} ({len(data)} bytes)")

    print(f"Stage A complete: {args.count} input files uploaded")


if __name__ == "__main__":
    main()
