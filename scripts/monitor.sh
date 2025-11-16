#!/bin/bash
# Quick monitor script - monitors latest running job
# Usage: ./scripts/monitor.sh [batch-number]
# Example: ./scripts/monitor.sh 3

set -e

BATCH="${1:-3}"  # Default to batch 3
JOB_NAME="prod-regular-screeners-batch-${BATCH}"

cd "$(dirname "$0")/.."
./scripts/monitor-batch-job.sh --job "${JOB_NAME}"
