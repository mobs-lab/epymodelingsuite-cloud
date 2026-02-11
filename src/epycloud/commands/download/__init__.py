"""Download command for fetching output plots from GCS."""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
