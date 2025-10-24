#!/usr/bin/env python3
"""
Stage B: Process individual tasks using BATCH_TASK_INDEX or TASK_INDEX.
Loads pickled input from storage (GCS or local), runs simulation, saves results.
"""

import os
import sys

# import pickle
import dill  # Use dill instead of pickle for better serialization support

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage

from flumodelingsuite.dispatcher import dispatch_runner


def main():
    # Get task index - supports both local (TASK_INDEX) and cloud (BATCH_TASK_INDEX)
    idx = int(os.getenv("TASK_INDEX", os.environ.get("BATCH_TASK_INDEX", "0")))

    # Get configuration
    config = storage.get_config()

    print(f"Starting Stage B task {idx}")
    print(f"  Storage mode: {config['mode']}")
    print(f"  Dir prefix: {config['dir_prefix']}")
    print(f"  Experiment ID: {config['exp_id']}")
    print(f"  Run ID: {config['run_id']}")
    if config["mode"] == "cloud":
        print(f"  Bucket: {config['bucket']}")

    # Load input file (workload from dispatcher)
    input_path = storage.get_path("inputs", f"input_{idx:04d}.pkl")
    print(f"Loading input: {input_path}")

    try:
        raw_data = storage.load_bytes(input_path)
        workload = dill.loads(raw_data)
        print(f"  Input loaded: {len(raw_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to load input: {e}")
        raise

    # Run simulation/calibration using dispatch_runner
    try:
        result = dispatch_runner(workload)
    except Exception as e:
        print(f"ERROR: Run failed: {e}")
        raise

    # Save results
    output_path = storage.get_path("results", f"result_{idx:04d}.pkl")
    print(f"Saving results: {output_path}")

    try:
        output_data = dill.dumps(result)
        storage.save_bytes(output_path, output_data)
        print(f"  Results saved: {len(output_data)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to save results: {e}")
        raise

    print(f"Task {idx} complete")


if __name__ == "__main__":
    main()
