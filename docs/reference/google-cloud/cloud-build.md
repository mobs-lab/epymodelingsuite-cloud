# Cloud Build

Google Cloud Build is a service that builds Docker images on Google Cloud infrastructure. The pipeline uses Cloud Build to build and push container images to Artifact Registry. For how the pipeline's Docker images are structured, see [Docker Images](../../architecture/docker-images.md).

<!--
link-card: https://docs.cloud.google.com/build/docs
    | title="Cloud Build documentation | Google Cloud"
    | description=false
-->

## Machine types

Cloud Build uses its own set of predefined machine types, separate from Compute Engine machine types:

| Machine Type | vCPU | Memory | Notes |
|--------------|------|--------|-------|
| `E2_MEDIUM` | 1 | 4 GB | Default |
| `E2_STANDARD_2` | 2 | 8 GB | |
| `E2_HIGHCPU_8` | 8 | 8 GB | Current default for this pipeline |
| `E2_HIGHCPU_32` | 32 | 32 GB | Fastest builds |

The pipeline defaults to `E2_HIGHCPU_8` for faster builds with more CPU available during dependency installation and compilation.

## Container testing

Cloud Build can run [container structure tests](https://github.com/GoogleContainerTools/container-structure-test) as part of the build steps to verify that built images have the expected files, commands, and environment variables.

The pipeline includes a test configuration at `docker/container-structure-test.yaml`. For details, see [Docker Images: Container structure tests](../../architecture/docker-images.md#container-structure-tests).

## Further reading

- [Cloud Build overview](https://cloud.google.com/build/docs/overview)
- [Cloud Build pricing](https://cloud.google.com/build/pricing)
