# Terraform Backend Configuration
# This file configures remote state storage in Google Cloud Storage
# State locking is handled automatically by GCS

terraform {
  backend "gcs" {
    bucket = "goingmerry-stonks-terraform-state-prod"
    prefix = "terraform/state"
    # State will be stored at: gs://goingmerry-stonks-terraform-state-prod/terraform/state/default.tfstate
  }
}
