#!/usr/bin/env python3
"""
Stage B: Process individual tasks using BATCH_TASK_INDEX or TASK_INDEX.
Loads pickled input from storage (GCS or local), runs simulation, saves results.
"""

import os
import sys
import pickle

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage


def run_simulation(model) -> dict:
    """
    Run the epydemix simulation.
    """

    res = model.run_simulations(start_date="2020-01-01", end_date="2020-12-31", Nsim=10)
    df_comp = res.get_quantiles_compartments()

    I_array = df_comp.query("quantile==0.5")["I_total"].values

    return I_array


def main():
    # Get task index - supports both local (TASK_INDEX) and cloud (BATCH_TASK_INDEX)
    idx = int(os.getenv("TASK_INDEX", os.environ.get("BATCH_TASK_INDEX", "0")))
    # GCS_BUCKET is only required in cloud mode
    bucket_name = os.getenv("GCS_BUCKET")
    in_prefix = os.environ["IN_PREFIX"]
    out_prefix = os.environ["OUT_PREFIX"]

    mode_info = storage.get_mode_info()
    print(f"Starting Stage B task {idx}")
    print(f"  Storage mode: {mode_info}")
    if mode_info["mode"] == "cloud":
        if not bucket_name:
            raise ValueError("GCS_BUCKET environment variable is required in cloud mode")
        print(f"  Bucket: {bucket_name}")
    else:
        bucket_name = None  # Not needed in local mode
    print(f"  Input prefix: {in_prefix}")
    print(f"  Output prefix: {out_prefix}")

    # Load input file
    input_key = f"{in_prefix}input_{idx:04d}.pkl"
    print(f"Loading input: {input_key}")

    try:
        raw_data = storage.load_bytes(bucket_name, input_key)
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
        storage.save_bytes(bucket_name, output_key, output_data)
        print(f"  Results saved: {len(output_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to save results: {e}")
        raise

    print(f"Task {idx} complete")


if __name__ == "__main__":
    main()
