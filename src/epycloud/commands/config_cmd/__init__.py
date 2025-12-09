"""Configuration management commands.

Available subcommands:
    epycloud config init          Initialize config directory
    epycloud config show          Show current configuration
    epycloud config edit          Edit base config in $EDITOR
    epycloud config edit-secrets  Edit secrets.yaml in $EDITOR
    epycloud config validate      Validate configuration
    epycloud config path          Show config directory path
    epycloud config get           Get config value
    epycloud config set           Set config value
    epycloud config list-envs     List available environments
"""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
