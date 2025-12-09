"""Logs command for viewing pipeline logs."""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
