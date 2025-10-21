# This project uses .env as the single source of truth for configuration.
# The Makefile reads .env and passes values to Terraform via -var flags.
#
# To configure this project:
#   1. Copy .env.example to .env
#   2. Edit .env with your values
#   3. Run: source .env && make tf-apply
#
# This file (terraform.tfvars) is NOT USED and can be safely deleted.
# It's kept for reference only.
