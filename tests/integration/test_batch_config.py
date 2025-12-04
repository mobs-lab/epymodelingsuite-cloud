"""Integration tests for batch configuration builder.

Tests use real implementations - no mocking needed since this is pure logic.
"""

from epycloud.commands.run.cloud.batch_config import build_batch_job_config


class TestBatchConfigStageA:
    """Test batch config generation for Stage A (Builder)."""

    def test_stage_a_basic_config(self):
        """Test basic Stage A config generation."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=8192,
            machine_type="",
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify labels
        assert config["labels"]["component"] == "epymodelingsuite"
        assert config["labels"]["stage"] == "builder"
        assert config["labels"]["exp_id"] == "test-sim"
        assert config["labels"]["run_id"] == "20251107-100000-abc12345"
        assert config["labels"]["managed-by"] == "manual"

        # Verify task groups
        assert len(config["taskGroups"]) == 1
        task_group = config["taskGroups"][0]
        assert task_group["taskCount"] == 1
        assert task_group["taskCountPerNode"] == 1

        # Verify container config
        task_spec = task_group["taskSpec"]
        runnable = task_spec["runnables"][0]["container"]
        assert runnable["imageUri"] == "us-central1-docker.pkg.dev/test-project/repo/image:latest"
        assert runnable["entrypoint"] == "/bin/bash"
        assert runnable["commands"] == ["/scripts/run_builder.sh"]

        # Verify environment variables
        env_vars = task_spec["environment"]["variables"]
        assert env_vars["EXECUTION_MODE"] == "cloud"
        assert env_vars["GCS_BUCKET"] == "test-bucket"
        assert env_vars["DIR_PREFIX"] == "pipeline/flu/"
        assert env_vars["EXP_ID"] == "test-sim"
        assert env_vars["RUN_ID"] == "20251107-100000-abc12345"
        assert env_vars["GITHUB_FORECAST_REPO"] == "owner/forecast-repo"

        # Verify compute resources
        compute = task_spec["computeResource"]
        assert compute["cpuMilli"] == 2000
        assert compute["memoryMib"] == 8192

        # Verify max run duration
        assert task_spec["maxRunDuration"] == "3600s"

        # Verify logs policy
        assert config["logsPolicy"]["destination"] == "CLOUD_LOGGING"

        # Verify allocation policy (no machine type)
        assert config["allocationPolicy"]["serviceAccount"]["email"] == "batch-sa@test-project.iam.gserviceaccount.com"
        assert "instances" not in config["allocationPolicy"]

    def test_stage_a_with_machine_type(self):
        """Test Stage A config with machine type specified."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=8000,
            memory_mib=32768,
            machine_type="c2-standard-8",  # Explicit machine type
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify allocation policy includes machine type
        assert "instances" in config["allocationPolicy"]
        instances = config["allocationPolicy"]["instances"][0]
        assert instances["policy"]["machineType"] == "c2-standard-8"

    def test_stage_a_with_c4d_machine_type(self):
        """Test Stage A config with C4D machine type (requires hyperdisk)."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=16000,
            memory_mib=65536,
            machine_type="c4d-standard-16",  # C4D requires special config
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify C4D-specific config
        instances = config["allocationPolicy"]["instances"][0]
        assert instances["policy"]["machineType"] == "c4d-standard-16"
        assert instances["installGpuDrivers"] is False
        assert instances["policy"]["provisioningModel"] == "STANDARD"
        assert instances["policy"]["bootDisk"]["type"] == "hyperdisk-balanced"
        assert instances["policy"]["bootDisk"]["sizeGb"] == 50

    def test_stage_a_with_task_count_per_node(self):
        """Test Stage A config with custom task_count_per_node."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=8192,
            machine_type="",
            max_run_duration=3600,
            task_count_per_node=4,  # Multiple tasks per node
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify task count per node
        assert config["taskGroups"][0]["taskCountPerNode"] == 4


class TestBatchConfigStageB:
    """Test batch config generation for Stage B (Runner)."""

    def test_stage_b_basic_config(self):
        """Test basic Stage B config generation."""
        config = build_batch_job_config(
            stage="B",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=5,  # Specific task
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=4000,
            memory_mib=16384,
            machine_type="",
            max_run_duration=7200,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify labels
        assert config["labels"]["stage"] == "runner"

        # Verify container config for Stage B
        runnable = config["taskGroups"][0]["taskSpec"]["runnables"][0]["container"]
        assert runnable["entrypoint"] == "python3"
        assert runnable["commands"] == ["-u", "/scripts/main_runner.py"]

        # Verify environment variables
        env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
        assert env_vars["EXECUTION_MODE"] == "cloud"
        assert env_vars["TASK_INDEX"] == "5"
        # Stage B doesn't need GITHUB_FORECAST_REPO
        assert "GITHUB_FORECAST_REPO" not in env_vars
        assert "NUM_TASKS" not in env_vars

        # Verify compute resources
        compute = config["taskGroups"][0]["taskSpec"]["computeResource"]
        assert compute["cpuMilli"] == 4000
        assert compute["memoryMib"] == 16384

    def test_stage_b_with_different_task_indices(self):
        """Test Stage B config with different task indices."""
        for task_idx in [0, 1, 10, 99]:
            config = build_batch_job_config(
                stage="B",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=task_idx,
                num_tasks=None,
                output_config=None,
                image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
                bucket_name="test-bucket",
                dir_prefix="pipeline/flu/",
                github_forecast_repo="owner/forecast-repo",
                project_id="test-project",
                cpu_milli=2000,
                memory_mib=8192,
                machine_type="",
                max_run_duration=3600,
                task_count_per_node=1,
                batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
            )

            env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
            assert env_vars["TASK_INDEX"] == str(task_idx)


class TestBatchConfigStageC:
    """Test batch config generation for Stage C (Output)."""

    def test_stage_c_basic_config(self):
        """Test basic Stage C config generation."""
        config = build_batch_job_config(
            stage="C",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=10,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=4000,
            memory_mib=16384,
            machine_type="",
            max_run_duration=7200,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify labels
        assert config["labels"]["stage"] == "output"

        # Verify container config for Stage C
        runnable = config["taskGroups"][0]["taskSpec"]["runnables"][0]["container"]
        assert runnable["entrypoint"] == "/bin/bash"
        assert runnable["commands"] == ["/scripts/run_output.sh"]

        # Verify environment variables
        env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
        assert env_vars["EXECUTION_MODE"] == "cloud"
        assert env_vars["NUM_TASKS"] == "10"
        assert env_vars["GITHUB_FORECAST_REPO"] == "owner/forecast-repo"
        assert env_vars["GCLOUD_PROJECT_ID"] == "test-project"
        assert env_vars["GITHUB_PAT_SECRET"] == "github-pat"
        assert env_vars["FORECAST_REPO_DIR"] == "/data/forecast/"
        assert env_vars["OUTPUT_CONFIG_FILE"] == ""  # Empty when not specified
        # Stage C doesn't need TASK_INDEX
        assert "TASK_INDEX" not in env_vars

    def test_stage_c_with_output_config(self):
        """Test Stage C config with specific output config file."""
        config = build_batch_job_config(
            stage="C",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=10,
            output_config="output_projection.yaml",  # Specific config
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=4000,
            memory_mib=16384,
            machine_type="",
            max_run_duration=7200,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify output config is set
        env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
        assert env_vars["OUTPUT_CONFIG_FILE"] == "output_projection.yaml"

    def test_stage_c_with_different_num_tasks(self):
        """Test Stage C config with different num_tasks values."""
        for num_tasks in [1, 10, 100, 1000]:
            config = build_batch_job_config(
                stage="C",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=0,
                num_tasks=num_tasks,
                output_config=None,
                image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
                bucket_name="test-bucket",
                dir_prefix="pipeline/flu/",
                github_forecast_repo="owner/forecast-repo",
                project_id="test-project",
                cpu_milli=2000,
                memory_mib=8192,
                machine_type="",
                max_run_duration=3600,
                task_count_per_node=1,
                batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
            )

            env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
            assert env_vars["NUM_TASKS"] == str(num_tasks)


class TestBatchConfigLabelSanitization:
    """Test label sanitization for GCP compliance."""

    def test_exp_id_with_slashes(self):
        """Test exp_id with slashes gets sanitized for labels."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test/nested/exp",  # Contains slashes
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=8192,
            machine_type="",
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Label should be sanitized (slashes replaced)
        assert "/" not in config["labels"]["exp_id"]
        # But environment variable should keep original
        env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
        assert env_vars["EXP_ID"] == "test/nested/exp"

    def test_run_id_sanitization(self):
        """Test run_id gets sanitized for labels."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=8192,
            machine_type="",
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # run_id label should be valid
        assert config["labels"]["run_id"] == "20251107-100000-abc12345"


class TestBatchConfigResourceVariations:
    """Test batch config with various resource configurations."""

    def test_large_cpu_memory_config(self):
        """Test config with large CPU and memory values."""
        config = build_batch_job_config(
            stage="B",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="pipeline/flu/",
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=96000,  # 96 CPUs
            memory_mib=393216,  # 384 GB
            machine_type="",
            max_run_duration=36000,  # 10 hours
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify resources
        compute = config["taskGroups"][0]["taskSpec"]["computeResource"]
        assert compute["cpuMilli"] == 96000
        assert compute["memoryMib"] == 393216
        assert config["taskGroups"][0]["taskSpec"]["maxRunDuration"] == "36000s"

    def test_custom_dir_prefix(self):
        """Test config with custom directory prefix."""
        config = build_batch_job_config(
            stage="A",
            exp_id="test-sim",
            run_id="20251107-100000-abc12345",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/test-project/repo/image:latest",
            bucket_name="test-bucket",
            dir_prefix="custom/path/to/pipeline/",  # Custom prefix
            github_forecast_repo="owner/forecast-repo",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=8192,
            machine_type="",
            max_run_duration=3600,
            task_count_per_node=1,
            batch_sa_email="batch-sa@test-project.iam.gserviceaccount.com",
        )

        # Verify custom dir_prefix
        env_vars = config["taskGroups"][0]["taskSpec"]["environment"]["variables"]
        assert env_vars["DIR_PREFIX"] == "custom/path/to/pipeline/"
