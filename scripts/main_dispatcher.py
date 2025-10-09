#!/usr/bin/env python3
"""
Stage A: Generate all input files for parallel processing.
Creates N pickled input files and uploads them to GCS.
"""

import os
import io
import pickle
import argparse
from google.cloud import storage
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
    bucket_name = os.environ["GCS_BUCKET"]
    out_prefix = os.getenv("OUT_PREFIX", "stageA/inputs/")
    sim_id = os.getenv("SIM_ID", "unknown")
    run_id = os.getenv("RUN_ID", "unknown")

    print(f"Starting Stage A: Generating {args.count} inputs")
    print(f"  Bucket: {bucket_name}")
    print(f"  Output prefix: {out_prefix}")
    print(f"  Sim ID: {sim_id}")
    print(f"  Run ID: {run_id}")
    print(f"  Seed: {args.seed}")

    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(bucket_name)

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

        # Upload to GCS
        blob_name = f"{out_prefix}input_{i:04d}.pkl"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(io.BytesIO(data), rewind=True)

        print(f"  Generated: {blob_name} ({len(data)} bytes)")

    print(f"Stage A complete: {args.count} input files uploaded")


if __name__ == "__main__":
    main()
