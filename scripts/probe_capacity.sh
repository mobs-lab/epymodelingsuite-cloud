#!/bin/bash
# Probe on-demand (STANDARD) VM capacity by creating VMs and deleting them right away.
#
# For every region x zone x machine type, bulk-creates COUNT VMs (accepting partial
# success), records how many were created and how long it took, then deletes them.
# Capacity changes minute to minute, so treat the result as a snapshot.
#
# Usage:
#   scripts/probe_capacity.sh [-r "us-central1 us-east5"] [-m "n4d-standard-2 c3d-standard-4"] \
#       [-n COUNT] [-p PARALLEL] [-P PROJECT] [-N NETWORK] [-o table|json]
#
#   -n COUNT     VMs to create per zone and machine type (default 1)
#   -o json      machine-readable output on stdout; progress goes to stderr
#
# Exit codes: 0 done, 1 setup error, 2 probe VMs were left behind (see "leftover_instances").
# Requires: gcloud, jq. Cost: each VM runs about a minute (billing minimum), a few cents per probe.
# Leftovers carry the label purpose=capacity-probe:
#   gcloud compute instances list --filter=labels.purpose=capacity-probe

set -uo pipefail

REGIONS="us-central1 us-east5"
MACHINES="n4d-standard-2 c4d-standard-2 n4-standard-2 c3d-standard-4 c3-standard-4"
COUNT=1
PARALLEL=8
PROJECT=$(gcloud config get-value project 2>/dev/null)
NETWORK=epymodelingsuite-network
OUTPUT=table

while getopts "r:m:n:p:P:N:o:h" opt; do
    case $opt in
        r) REGIONS=$OPTARG ;;
        m) MACHINES=$OPTARG ;;
        n) COUNT=$OPTARG ;;
        p) PARALLEL=$OPTARG ;;
        P) PROJECT=$OPTARG ;;
        N) NETWORK=$OPTARG ;;
        o) OUTPUT=$OPTARG ;;
        *) sed -n '2,19p' "$0"; exit 0 ;;
    esac
done
[[ $OUTPUT == table || $OUTPUT == json ]] || { echo "-o must be table or json" >&2; exit 1; }
[[ -n $PROJECT ]] || { echo "No project: pass -P or set gcloud config project" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

RUN_ID=$(date +%H%M%S)$((RANDOM % 100))
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
export PROJECT COUNT RUN_ID

list_leftovers() {
    gcloud compute instances list --project="$PROJECT" \
        --filter="labels.purpose=capacity-probe AND labels.probe-run=$RUN_ID" \
        --format="value(name,zone.basename())" 2>/dev/null
}

cleanup() {
    list_leftovers | while read -r name zone; do
        gcloud compute instances delete "$name" --zone="$zone" --project="$PROJECT" --quiet >/dev/null 2>&1 &
    done
    wait
}
trap 'cleanup; exit 130' INT TERM

# One probe: create COUNT VMs in one zone, print a TSV row, delete them.
# Row: region zone machine requested created seconds status message
probe() {
    local region=$1 zone=$2 machine=$3 subnet=$4
    local family=${machine%%-*} disk=pd-balanced
    case $family in c4* | n4* | c3* | h3*) disk=hyperdisk-balanced ;; esac
    local name="capprobe-${RUN_ID}-${zone##*-}-${machine//[^a-z0-9]/}"
    name=${name:0:55}
    local start=$SECONDS out created=0 status message=""
    out=$(gcloud compute instances bulk create --project="$PROJECT" --zone="$zone" \
        --name-pattern="${name}-#" --count="$COUNT" --min-count=1 \
        --machine-type="$machine" --image-family=cos-stable --image-project=cos-cloud \
        --boot-disk-type="$disk" --boot-disk-size=10GB --subnet="$subnet" --no-address \
        --labels="purpose=capacity-probe,probe-run=$RUN_ID" 2>&1)
    [[ $out =~ created:\ ([0-9]+) ]] && created=${BASH_REMATCH[1]}
    if ((created == COUNT)); then status=ok
    elif ((created > 0)); then status=partial
    elif [[ $out == *RESOURCE_POOL_EXHAUSTED* || $out == *STOCKOUT* || $out == *"does not have enough resources"* ]]; then status=stockout
    elif [[ $out == *QUOTA* || $out == *quota* ]]; then status=quota
    else status=error
    fi
    # Keep the line that explains the failure, not the bulk-create DNS warning.
    if [[ $status != ok ]]; then
        message=$(grep -m1 -iE "exhausted|enough resources|stockout|quota" <<<"$out" ||
            grep -m1 -i "error" <<<"$out" || head -1 <<<"$out")
        message=$(tr '\t' ' ' <<<"$message" | cut -c1-300)
    fi
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$region" "$zone" "$machine" "$COUNT" "$created" "$((SECONDS - start))" "$status" "$message"
    gcloud compute instances list --project="$PROJECT" --zones="$zone" \
        --filter="labels.probe-run=$RUN_ID AND name~^${name}-" --format="value(name)" 2>/dev/null |
        xargs -r gcloud compute instances delete --zone="$zone" --project="$PROJECT" --quiet >/dev/null 2>&1
}
export -f probe

jobs_file=$(mktemp)
rows_file=$(mktemp)
trap 'rm -f "$jobs_file" "$rows_file"' EXIT
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

echo "Probing $(wc -l <"$jobs_file") region/zone/machine combinations (run $RUN_ID)..." >&2
xargs -P "$PARALLEL" -L 1 bash -c 'probe "$@"' _ <"$jobs_file" | sort >"$rows_file"

cleanup
leftovers=$(list_leftovers | wc -l)

if [[ $OUTPUT == json ]]; then
    jq -R -s \
        --arg project "$PROJECT" --arg started_at "$STARTED_AT" \
        --arg finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg run_id "$RUN_ID" \
        --argjson count "$COUNT" --argjson leftovers "$leftovers" \
        --arg regions "$REGIONS" --arg machines "$MACHINES" '
        [split("\n")[] | select(length > 0) | split("\t") | {
            region: .[0], zone: .[1], machine_type: .[2],
            requested: (.[3] | tonumber), created: (.[4] | tonumber),
            seconds: (.[5] | tonumber), status: .[6], message: .[7]
        }] as $results
        | {
            project: $project, run_id: $run_id, started_at: $started_at, finished_at: $finished_at,
            provisioning_model: "STANDARD", count_per_zone: $count,
            regions: ($regions | split(" ")), machine_types: ($machines | split(" ")),
            results: $results,
            summary: ($results | group_by([.region, .machine_type]) | map({
                region: .[0].region, machine_type: .[0].machine_type,
                zones_total: length,
                zones_ok: map(select(.status == "ok")) | length,
                zones_ok_list: map(select(.status == "ok") | .zone),
                availability: (if all(.status == "ok") then "available"
                               elif any(.status == "ok" or .status == "partial") then "limited"
                               else "unavailable" end)
            })),
            leftover_instances: $leftovers
        }' "$rows_file"
else
    { printf "REGION\tZONE\tMACHINE\tCREATED\tTIME\tSTATUS\n"
      awk -F'\t' '{printf "%s\t%s\t%s\t%s/%s\t%ss\t%s\n", $1, $2, $3, $5, $4, $6, $7}' "$rows_file"
    } | column -t -s $'\t'
    ((leftovers == 0)) || echo "WARNING: $leftovers probe VMs left behind (label probe-run=$RUN_ID)" >&2
fi

((leftovers == 0)) || exit 2
