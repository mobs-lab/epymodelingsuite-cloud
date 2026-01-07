"""Unit tests for workflow command parser."""

import argparse

from epycloud.commands.workflow.parser import register_parser


class TestWorkflowParser:
    """Test workflow parser registration."""

    def test_register_parser(self):
        """Test workflow parser is registered with subcommands."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        register_parser(subparsers)

        # Parse workflow command
        args = parser.parse_args(["workflow", "list"])
        assert args.command == "workflow"
        assert args.workflow_subcommand == "list"

    def test_workflow_list_defaults(self):
        """Test workflow list command defaults."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        register_parser(subparsers)

        args = parser.parse_args(["workflow", "list"])
        assert args.limit == 20
        assert args.status is None
        assert args.exp_id is None

    def test_workflow_describe(self):
        """Test workflow describe command."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        register_parser(subparsers)

        args = parser.parse_args(["workflow", "describe", "exec-123"])
        assert args.workflow_subcommand == "describe"
        assert args.execution_id == "exec-123"

    def test_workflow_cancel(self):
        """Test workflow cancel command."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        register_parser(subparsers)

        args = parser.parse_args(["workflow", "cancel", "exec-123"])
        assert args.workflow_subcommand == "cancel"
        assert args.execution_id == "exec-123"
        assert args.only_workflow is False

    def test_workflow_logs(self):
        """Test workflow logs command."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        register_parser(subparsers)

        args = parser.parse_args(["workflow", "logs", "exec-123"])
        assert args.workflow_subcommand == "logs"
        assert args.execution_id == "exec-123"
        assert args.follow is False
        assert args.tail == 100
