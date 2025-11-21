# Outputs for Cloud Batch Jobs Module

output "batch_job_names" {
  description = "Cloud Batch job names for regular screeners (all batches)"
  value = {
    for key, job in google_batch_job.regular_screeners_batch :
    key => job.name
  }
}

output "batch_job_ids" {
  description = "Cloud Batch job IDs for monitoring and automation"
  value = {
    for key, job in google_batch_job.regular_screeners_batch :
    key => job.id
  }
}

output "scheduler_names" {
  description = "Cloud Scheduler job names for batch triggers"
  value = {
    for key, scheduler in google_cloud_scheduler_job.trigger_regular_screeners_batch :
    key => scheduler.name
  }
}

output "batch_info" {
  description = "Complete batch configuration including schedules and job names"
  value = {
    for key, batch in local.enabled_batches :
    key => {
      batch_number    = batch.number
      schedule        = batch.schedule
      time            = batch.time_label
      job_name        = google_batch_job.regular_screeners_batch[key].name
      scheduler_name  = google_cloud_scheduler_job.trigger_regular_screeners_batch[key].name
      machine_type    = var.vm_machine_type
    }
  }
}

output "cost_estimate" {
  description = "Estimated monthly cost for Cloud Batch with Spot VMs"
  value = {
    vm_type              = var.vm_machine_type
    spot_hourly_rate     = "~$0.0066/hour (e2-medium Spot)"
    runtime_per_batch    = "~95 minutes (~1.58 hours)"
    daily_cost           = "5 batches × 1.58h × $0.0066 = ~$0.052"
    monthly_cost         = "20 business days × $0.052 = ~$1.04"
    annual_cost          = "~$12.48/year"
    savings_vs_cloud_run = "96.5% ($347.52/year)"
  }
}
