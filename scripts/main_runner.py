#!/usr/bin/env python3
"""
Stage B: Process individual tasks using BATCH_TASK_INDEX.
Loads pickled input from GCS, runs simulation, saves results.
"""

import os
import pickle
from google.cloud import storage


def load_input_bytes(bucket_name: str, path: str) -> bytes:
    """Load bytes from GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    return bucket.blob(path).download_as_bytes()


def save_bytes(bucket_name: str, path: str, data: bytes):
    """Save bytes to GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(path).upload_from_string(data)


def run_simulation(model) -> dict:
    """
    Run the epydemix simulation.
    """

    res = model.run_simulations(start_date="2020-01-01", end_date="2020-12-31", Nsim=10)
    df_comp = res.get_quantiles_compartments()

    I_array = df_comp.query("quantile==0.5")["I_total"].values

    return I_array


def main():
    # Get task index from Batch environment
    idx = int(os.environ["BATCH_TASK_INDEX"])
    bucket_name = os.environ["GCS_BUCKET"]
    in_prefix = os.environ["IN_PREFIX"]
    out_prefix = os.environ["OUT_PREFIX"]

    print(f"Starting Stage B task {idx}")
    print(f"  Bucket: {bucket_name}")
    print(f"  Input prefix: {in_prefix}")
    print(f"  Output prefix: {out_prefix}")

    # Load input file
    input_key = f"{in_prefix}input_{idx:04d}.pkl"
    print(f"Loading input: {input_key}")

    try:
        raw_data = load_input_bytes(bucket_name, input_key)
        model = pickle.loads(raw_data)
        print(f"  Input loaded: {len(raw_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to load input: {e}")
        raise

    # Run simulation
    try:
        results = run_simulation(model)
    except Exception as e:
        print(f"ERROR: Simulation failed: {e}")
        raise

    # Save results
    output_key = f"{out_prefix}result_{idx:04d}.pkl"
    print(f"Saving results: {output_key}")

    try:
        output_data = pickle.dumps(results)
        save_bytes(bucket_name, output_key, output_data)
        print(f"  Results saved: {len(output_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to save results: {e}")
        raise

    print(f"Task {idx} complete")


if __name__ == "__main__":
    main()
