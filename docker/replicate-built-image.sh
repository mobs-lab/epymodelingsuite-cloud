#!/usr/bin/env bash
set -euo pipefail

# Push the same local image everywhere; never resolve a mutable remote tag.
docker push "$SOURCE_IMAGE"
for region in $REPLICA_REGIONS; do
    destination="${region}-docker.pkg.dev/${IMAGE_PATH}"
    docker tag "$SOURCE_IMAGE" "$destination"
    docker push "$destination"
done
