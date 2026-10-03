#!/bin/bash
# Probe on-demand (STANDARD) VM capacity by creating VMs and deleting them right away.
#
# For every region x zone x machine type, bulk-creates COUNT VMs (accepting partial
# success), records how many were created and how long it took, then deletes them.
# Capacity changes minute to minute, so treat the result as a snapshot.
#
# Usage:
#   scripts/probe_capacity.sh [-r "us-central1 us-east5"] [-m "c4d-standard-2 c3d-standard-4"] \
#                             [-n COUNT] [-p PARALLEL] [-P PROJECT] [-N NETWORK]
#
# Cost: each VM runs about one minute (billing minimum), so a few cents per probe.
# Leftovers carry the label purpose=capacity-probe:
#   gcloud compute instances list --filter=labels.purpose=capacity-probe

set -uo pipefail

REGIONS="us-central1 us-east5"
MACHINES="c4d-standard-2 n4d-standard-2 n4-standard-2 c3d-standard-4 c3-standard-4"
COUNT=1
PARALLEL=8
PROJECT=$(gcloud config get-value project 2>/dev/null)
NETWORK=epymodelingsuite-network

while getopts "r:m:n:p:P:N:h" opt; do
    case $opt in
        r) REGIONS=$OPTARG ;;
        m) MACHINES=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        p) PARALLEL=$OPTARG ;;
        P) PROJECT=$OPTARG ;;
        N) NETWORK=$OPTARG ;;
        *) sed -n '2,15p' "$0"; exit 0 ;;
    esac
done

RUN_ID=$(date +%H%M%S)
export PROJECT COUNT RUN_ID

cleanup() {
    gcloud compute instances list --project="$PROJECT" \
        --filter="labels.purpose=capacity-probe AND labels.probe-run=$RUN_ID" \
        --format="value(name,zone.basename())" 2>/dev/null |
        while read -r name zone; do
            gcloud compute instances delete "$name" --zone="$zone" --project="$PROJECT" --quiet >/dev/null 2>&1 &
        done
    wait
}
trap cleanup EXIT INT TERM

# One probe: create COUNT VMs in one zone, report, delete.
probe() {
    local region=$1 zone=$2 machine=$3 subnet=$4
    local family=${machine%%-*} disk=pd-balanced
    case $family in c4* | n4* | c3* | h3*) disk=hyperdisk-balanced ;; esac
    local name="capprobe-${RUN_ID}-${zone##*-}-${machine//[^a-z0-9]/}"
    local start=$SECONDS out created=0 status
    out=$(gcloud compute instances bulk create --project="$PROJECT" --zone="$zone" \
        --name-pattern="${name:0:55}-#" --count="$COUNT" --min-count=1 \
        --machine-type="$machine" --image-family=cos-stable --image-project=cos-cloud \
        --boot-disk-type="$disk" --boot-disk-size=10GB --subnet="$subnet" --no-address \
        --labels="purpose=capacity-probe,probe-run=$RUN_ID" 2>&1)
    [[ $out =~ created:\ ([0-9]+) ]] && created=${BASH_REMATCH[1]}
    if ((created == COUNT)); then status=OK
    elif ((created > 0)); then status=PARTIAL
    elif [[ $out == *RESOURCE_POOL_EXHAUSTED* || $out == *STOCKOUT* || $out == *"does not have enough resources"* ]]; then status=STOCKOUT
    elif [[ $out == *QUOTA* || $out == *quota* ]]; then status=QUOTA
    else status="ERROR: $(tr '\n' ' ' <<<"$out" | cut -c1-120)"
    fi
    printf "%s\t%s\t%s\t%s/%s\t%ss\t%s\n" "$region" "$zone" "$machine" "$created" "$COUNT" "$((SECONDS - start))" "$status"
    gcloud compute instances list --project="$PROJECT" --zones="$zone" \
        --filter="labels.probe-run=$RUN_ID AND name~^${name:0:55}" --format="value(name)" 2>/dev/null |
        xargs -r gcloud compute instances delete --zone="$zone" --project="$PROJECT" --quiet >/dev/null 2>&1
}
export -f probe

jobs_file=$(mktemp)
for region in $REGIONS; do
    subnet=$(gcloud compute networks subnets list --project="$PROJECT" --network="$NETWORK" \
        --filter="region:$region" --format="value(selfLink)" 2>/dev/null | head -1)
    if [[ -z $subnet ]]; then
        echo "skip $region: no subnet in network $NETWORK" >&2
        continue
    fi
    for machine in $MACHINES; do
        for zone in $(gcloud compute machine-types list --project="$PROJECT" \
            --filter="name=$machine AND zone~^$region-" --format="value(zone.basename())" 2>/dev/null | sort); do
            echo "$region $zone $machine $subnet" >>"$jobs_file"
        done
    done
done

printf "REGION\tZONE\tMACHINE\tCREATED\tTIME\tSTATUS\n"
xargs -P "$PARALLEL" -L 1 bash -c 'probe "$@"' _ <"$jobs_file" | sort
rm -f "$jobs_file"
