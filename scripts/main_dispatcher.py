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

    # Get environment variables
    # GCS_BUCKET is only required in cloud mode
    bucket_name = os.getenv("GCS_BUCKET")
    out_prefix = os.getenv("OUT_PREFIX", "stageA/inputs/")
    sim_id = os.getenv("SIM_ID", "unknown")
    run_id = os.getenv("RUN_ID", "unknown")

    mode_info = storage.get_mode_info()
    print(f"Starting Stage A: Generating {args.count} inputs")
    print(f"  Storage mode: {mode_info}")
    if mode_info["mode"] == "cloud":
        if not bucket_name:
            raise ValueError("GCS_BUCKET environment variable is required in cloud mode")
        print(f"  Bucket: {bucket_name}")
    else:
        bucket_name = None  # Not needed in local mode
    print(f"  Output prefix: {out_prefix}")
    print(f"  Sim ID: {sim_id}")
    print(f"  Run ID: {run_id}")
    print(f"  Seed: {args.seed}")

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
        blob_name = f"{out_prefix}input_{i:04d}.pkl"
        storage.save_bytes(bucket_name, blob_name, data)

        print(f"  Generated: {blob_name} ({len(data)} bytes)")

    print(f"Stage A complete: {args.count} input files uploaded")


if __name__ == "__main__":
    main()
