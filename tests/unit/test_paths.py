"""Unit tests for paths module YAML extension handling."""

import logging
from unittest.mock import patch

import pytest

from epycloud.lib.paths import (
    _list_yaml_files,
    _resolve_yaml_file,
    get_config_file,
    get_environment_file,
    get_profile_file,
    get_secrets_file,
    list_environments,
)


class TestResolveYamlFile:
    """Tests for _resolve_yaml_file helper."""

    def test_returns_yaml_path_when_yaml_exists(self, tmp_path):
        (tmp_path / "foo.yaml").write_text("x: 1\n")
        result = _resolve_yaml_file(tmp_path, "foo")
        assert result == tmp_path / "foo.yaml"

    def test_returns_yml_path_when_only_yml_exists(self, tmp_path):
        (tmp_path / "foo.yml").write_text("x: 1\n")
        result = _resolve_yaml_file(tmp_path, "foo")
        assert result == tmp_path / "foo.yml"

    def test_returns_yaml_path_when_neither_exists(self, tmp_path):
        result = _resolve_yaml_file(tmp_path, "foo")
        assert result == tmp_path / "foo.yaml"

    def test_prefers_yaml_when_both_exist(self, tmp_path):
        (tmp_path / "foo.yaml").write_text("x: 1\n")
        (tmp_path / "foo.yml").write_text("x: 2\n")
        result = _resolve_yaml_file(tmp_path, "foo")
        assert result == tmp_path / "foo.yaml"

    def test_logs_warning_when_both_exist(self, tmp_path, caplog):
        (tmp_path / "foo.yaml").write_text("x: 1\n")
        (tmp_path / "foo.yml").write_text("x: 2\n")
        with caplog.at_level(logging.WARNING, logger="epycloud.lib.paths"):
            _resolve_yaml_file(tmp_path, "foo")
        assert "Both foo.yaml and foo.yml" in caplog.text

    def test_no_warning_when_only_yaml(self, tmp_path, caplog):
        (tmp_path / "foo.yaml").write_text("x: 1\n")
        with caplog.at_level(logging.WARNING, logger="epycloud.lib.paths"):
            _resolve_yaml_file(tmp_path, "foo")
        assert caplog.text == ""

    def test_no_warning_when_only_yml(self, tmp_path, caplog):
        (tmp_path / "foo.yml").write_text("x: 1\n")
        with caplog.at_level(logging.WARNING, logger="epycloud.lib.paths"):
            _resolve_yaml_file(tmp_path, "foo")
        assert caplog.text == ""


class TestListYamlFiles:
    """Tests for _list_yaml_files helper."""

    def test_lists_yaml_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "b.yaml").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.name for f in result] == ["a.yaml", "b.yaml"]

    def test_lists_yml_files(self, tmp_path):
        (tmp_path / "a.yml").write_text("")
        (tmp_path / "b.yml").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.name for f in result] == ["a.yml", "b.yml"]

    def test_lists_mixed_extensions(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "b.yml").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.name for f in result] == ["a.yaml", "b.yml"]

    def test_deduplicates_preferring_yaml(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "a.yml").write_text("")
        (tmp_path / "b.yml").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.name for f in result] == ["a.yaml", "b.yml"]

    def test_logs_warning_for_duplicates(self, tmp_path, caplog):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "a.yml").write_text("")
        with caplog.at_level(logging.WARNING, logger="epycloud.lib.paths"):
            _list_yaml_files(tmp_path)
        assert "Both a.yaml and a.yml" in caplog.text

    def test_empty_directory(self, tmp_path):
        result = _list_yaml_files(tmp_path)
        assert result == []

    def test_ignores_non_yaml_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "b.txt").write_text("")
        (tmp_path / "c.json").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.name for f in result] == ["a.yaml"]

    def test_sorted_by_stem(self, tmp_path):
        (tmp_path / "z.yaml").write_text("")
        (tmp_path / "a.yml").write_text("")
        (tmp_path / "m.yaml").write_text("")
        result = _list_yaml_files(tmp_path)
        assert [f.stem for f in result] == ["a", "m", "z"]


class TestWrapperYmlFallback:
    """Verify each wrapper delegates to _resolve_yaml_file correctly.

    Core resolution logic (yaml default, yml fallback, yaml preferred, warnings)
    is covered by TestResolveYamlFile. These tests only confirm each wrapper
    passes the right directory and filename through to _resolve_yaml_file.
    """

    @pytest.mark.parametrize(
        "wrapper_call, subdir, filename",
        [
            (lambda: get_config_file(), "", "config"),
            (lambda: get_secrets_file(), "", "secrets"),
            (lambda: get_profile_file("flu"), "profiles", "flu"),
            (lambda: get_environment_file("dev"), "environments", "dev"),
        ],
        ids=["config", "secrets", "profile", "environment"],
    )
    def test_yml_fallback(self, tmp_path, wrapper_call, subdir, filename):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        target_dir = (config_dir / subdir) if subdir else config_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / f"{filename}.yml").write_text("key: val\n")

        with patch("epycloud.lib.paths.get_config_dir", return_value=config_dir):
            result = wrapper_call()
        assert result == target_dir / f"{filename}.yml"


class TestListEnvironmentsYmlSupport:
    """Tests for list_environments with .yml support."""

    @patch("epycloud.lib.paths.get_config_dir")
    def test_lists_yml_environments(self, mock_config_dir, tmp_path):
        config_dir = tmp_path / "config"
        envs_dir = config_dir / "environments"
        envs_dir.mkdir(parents=True)
        (envs_dir / "dev.yml").write_text("")
        (envs_dir / "prod.yml").write_text("")
        mock_config_dir.return_value = config_dir

        result = list_environments()
        assert result == ["dev", "prod"]

    @patch("epycloud.lib.paths.get_config_dir")
    def test_lists_mixed_extensions(self, mock_config_dir, tmp_path):
        config_dir = tmp_path / "config"
        envs_dir = config_dir / "environments"
        envs_dir.mkdir(parents=True)
        (envs_dir / "dev.yaml").write_text("")
        (envs_dir / "prod.yml").write_text("")
        mock_config_dir.return_value = config_dir

        result = list_environments()
        assert result == ["dev", "prod"]

    @patch("epycloud.lib.paths.get_config_dir")
    def test_deduplicates_when_both_exist(self, mock_config_dir, tmp_path):
        config_dir = tmp_path / "config"
        envs_dir = config_dir / "environments"
        envs_dir.mkdir(parents=True)
        (envs_dir / "dev.yaml").write_text("")
        (envs_dir / "dev.yml").write_text("")
        (envs_dir / "prod.yml").write_text("")
        mock_config_dir.return_value = config_dir

        result = list_environments()
        assert result == ["dev", "prod"]
