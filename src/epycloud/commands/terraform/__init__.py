"""Terraform command for infrastructure management.

Available subcommands:
    epycloud terraform init     Initialize Terraform
    epycloud terraform plan     Plan infrastructure changes
    epycloud terraform apply    Apply infrastructure changes
    epycloud terraform destroy  Destroy infrastructure
    epycloud terraform output   Show Terraform outputs
    epycloud tf                 Alias for 'terraform'
"""

from .handlers import handle
from .parser import register_parser

__all__ = ["register_parser", "handle"]
