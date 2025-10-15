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

    # Get configuration
    config = storage.get_config()

    print(f"Starting Stage B task {idx}")
    print(f"  Storage mode: {config['mode']}")
    print(f"  Dir prefix: {config['dir_prefix']}")
    print(f"  Sim ID: {config['sim_id']}")
    print(f"  Run ID: {config['run_id']}")
    if config['mode'] == 'cloud':
        print(f"  Bucket: {config['bucket']}")

    # Load input file
    input_path = storage.get_path("inputs", f"input_{idx:04d}.pkl")
    print(f"Loading input: {input_path}")

    try:
        raw_data = storage.load_bytes(input_path)
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
    output_path = storage.get_path("results", f"result_{idx:04d}.pkl")
    print(f"Saving results: {output_path}")

    try:
        output_data = pickle.dumps(results)
        storage.save_bytes(output_path, output_data)
        print(f"  Results saved: {len(output_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to save results: {e}")
        raise

    print(f"Task {idx} complete")


if __name__ == "__main__":
    main()
