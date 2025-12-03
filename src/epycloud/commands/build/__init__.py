"""Build command for Docker image management.

Available commands:
    epycloud build cloud     Submit to Cloud Build (async, default)
    epycloud build local     Build locally and push to registry
    epycloud build dev       Build locally only (no push)
    epycloud build status    Display recent/ongoing Cloud Build jobs
"""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
