"""Run command for executing pipeline stages and workflows.

Available subcommands:
    epycloud run workflow    Submit complete workflow (all stages: A → B → C)
    epycloud run job         Run a single stage or task (A, B, or C)
"""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
