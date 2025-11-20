# Cloud Batch Migration Configuration
#
# This file manages the phased migration from Cloud Run Jobs to Cloud Batch + Spot VMs.
#
# MIGRATION PHASES:
# Phase 1 (Week 1): Enable batch-1 only (pilot)
# Phase 2 (Week 2): Enable batch-1, batch-2, batch-3 (60% migration)
# Phase 3 (Week 3): Enable all 5 batches (100% migration)
# Phase 4 (Week 4): Decommission Cloud Run Jobs
#
# INSTRUCTIONS:
# 1. Uncomment the module block below to enable Cloud Batch
# 2. Use enable_batches variable to control which batches are active
# 3. Monitor both systems in parallel during migration
# 4. Once validated, disable Cloud Run schedulers in scheduled_jobs module

# ============================================================================
# PHASE 1: PILOT (BATCH 1 ONLY)
# ============================================================================
# Uncomment this block to start Phase 1

# module "batch_jobs_pilot" {
#   source = "../../modules/batch_jobs"
#
#   project_id              = var.project_id
#   region                  = var.region
#   scheduler_region        = var.scheduler_region
#   environment             = var.environment
#   service_account_email   = module.backend.service_account_email
#   polygon_api_key_secret  = module.secrets.polygon_api_key_id
#   docker_image            = var.docker_image
#   job_timeout_seconds     = 10800  # 3 hours
#   vm_machine_type         = "e2-medium"
#   rate_limit_per_minute   = 58
#
#   # PHASE 1: Enable only batch-1 for pilot
#   enable_batches = {
#     batch-1 = true
#     batch-2 = false
#     batch-3 = false
#     batch-4 = false
#     batch-5 = false
#   }
# }

# ============================================================================
# PHASE 2: EXPAND (BATCH 1-3)
# ============================================================================
# After Phase 1 validation (5 days), uncomment and change enable_batches:

# module "batch_jobs_pilot" {
#   source = "../../modules/batch_jobs"
#
#   project_id              = var.project_id
#   region                  = var.region
#   scheduler_region        = var.scheduler_region
#   environment             = var.environment
#   service_account_email   = module.backend.service_account_email
#   polygon_api_key_secret  = module.secrets.polygon_api_key_id
#   docker_image            = var.docker_image
#   job_timeout_seconds     = 10800
#   vm_machine_type         = "e2-medium"
#   rate_limit_per_minute   = 58
#
#   # PHASE 2: Enable batches 1-3 (60% migration)
#   enable_batches = {
#     batch-1 = true
#     batch-2 = true
#     batch-3 = true
#     batch-4 = false
#     batch-5 = false
#   }
# }

# ============================================================================
# PHASE 3: FULL MIGRATION (ALL BATCHES)
# ============================================================================
# After Phase 2 validation (5 days), change enable_batches:

# module "batch_jobs" {
#   source = "../../modules/batch_jobs"
#
#   project_id              = var.project_id
#   region                  = var.region
#   scheduler_region        = var.scheduler_region
#   environment             = var.environment
#   service_account_email   = module.backend.service_account_email
#   polygon_api_key_secret  = module.secrets.polygon_api_key_id
#   docker_image            = var.docker_image
#   job_timeout_seconds     = 10800
#   vm_machine_type         = "e2-medium"
#   rate_limit_per_minute   = 58
#
#   # PHASE 3: Enable all batches (100% migration)
#   enable_batches = {
#     batch-1 = true
#     batch-2 = true
#     batch-3 = true
#     batch-4 = true
#     batch-5 = true
#   }
# }

# ============================================================================
# OUTPUTS
# ============================================================================

# output "batch_migration_status" {
#   description = "Cloud Batch migration status and job information"
#   value       = module.batch_jobs.batch_info
# }
#
# output "batch_cost_estimate" {
#   description = "Estimated cost savings with Cloud Batch"
#   value       = module.batch_jobs.cost_estimate
# }
