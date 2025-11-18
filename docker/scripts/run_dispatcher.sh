#!/bin/bash
set -euo pipefail

# Universal dispatcher script for all pipeline stages
# Routes to the correct stage script based on STAGE environment variable

STAGE="${STAGE:-}"

if [ -z "$STAGE" ]; then
    echo "ERROR: STAGE environment variable must be set"
    echo "Valid values: builder, runner, output"
    exit 1
fi

case "$STAGE" in
    builder|A)
        exec /scripts/run_builder.sh "$@"
        ;;
    runner|B)
        exec python3 -u /scripts/main_runner.py "$@"
        ;;
    output|C)
        exec /scripts/run_output.sh "$@"
        ;;
    *)
        echo "ERROR: Invalid STAGE='$STAGE'"
        echo "Valid values: builder, runner, output (or A, B, C)"
        exit 1
        ;;
esac
