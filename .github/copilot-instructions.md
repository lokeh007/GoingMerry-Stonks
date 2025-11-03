## Purpose

This file gives concise, repository-specific guidance for an AI coding agent to be immediately productive in the stock-tools repo. It focuses on the real architecture, developer workflows, naming and packaging conventions, test commands, and concrete file examples.

## Big-picture architecture (September 2025 - Current State)

**Container-based serverless platform** with SOLID architecture principles:
- **Data stores**: DynamoDB table `MarketSignals`, S3 buckets prefixed `thousandsunny-*`, CloudWatch metrics/namespaces
- **Container runtime**: AWS Lambda with ECR container images, shared base image for 40-50x faster builds
- **SOLID analytics engine**: Complete refactoring following SOLID principles with expert enhancement modules (performance monitoring, circuit breakers, async processing, data validation, error recovery, config management, health checks)
- **Orchestration**: Step Functions workflows for automated daily collection (6:05 AM/8:05 PM EST)
- **Frontend**: dash-thousandsunny (Plotly) dashboard with Python/Lambda container runtime
- **Common patterns**: Dependency injection containers (`src/common/`), protocol-based interfaces, centralized AWS client factory

## Essential developer workflows (concrete commands)
- **Build containers**: `./build-containers.sh <function-name>` (e.g., `./build-containers.sh analytics-engine --test --health-check`) 
  - Uses shared base image from `containers/base/Dockerfile` with pre-installed pandas/numpy for performance
  - Builds with `DOCKER_BUILDKIT=0` for Lambda v2 manifest compatibility 
  - Includes automatic testing and health validation
- **Test runner**: `python run_tests.py` (root). Key options: `--coverage`, `--install-deps`, `--lambda <name>`, `--together`
  - Example: `python run_tests.py --lambda analytics --coverage` runs analytics-engine tests with coverage
  - Updated LAMBDA_DIRS includes 19 lambda functions (see run_tests.py lines 35-59)
- **Per-lambda tests**: `python -m pytest test_lambda.py` or `python -m pytest test_analytics.py` 
- **Deploy infra**: `cd terraform/environments/prod && terraform init && terraform apply` (single prod env)
- **Dashboard testing**: Function URL endpoint testing and Plotly performance validation

## Project-specific conventions (concrete rules)
- **Python runtime**: Python 3.12 on Amazon Linux 2 (container base image `public.ecr.aws/lambda/python:3.12`)
- **Container structure**: Each lambda in `src/<name>/` with `Dockerfile`, `lambda_function.py`, `requirements.txt`, `test_*.py`
- **Shared dependencies**: Base image `containers/base/Dockerfile` contains pandas, numpy, boto3 for 40-50x faster builds
- **Handler pattern**: All lambdas use `lambda_function.lambda_handler` with standardized JSON response `{statusCode, body}`
- **SOLID architecture**: Analytics engine follows dependency injection with protocols (`src/analytics_engine/*.py`)
- **Common utilities**: Centralized AWS clients and DI containers in `src/common/` (aws_clients.py, dependencies.py)
- **Testing**: pytest.ini configured with markers `unit`, `integration`, `slow`, `aws`, `network`. Coverage target: 15% minimum
- **Step Functions**: Three orchestration workflows in `step-functions/` for phase 3 production automation

## Integration points and environment variables to watch
- DynamoDB: table name `MarketSignals` (used by analytics engine). See `src/analytics_engine/README.md`.
- S3: default bucket env var names seen are `S3_BUCKET` and `S3_BUCKET_NAME` (value examples: `thousandsunny-raw-data`). Check each lambda's README for exact names.
- ENVIRONMENT or ENVIRONMENT-like flags (`ENVIRONMENT`, `ENV`) are frequently used to switch dev/prod behavior.
- CloudWatch namespaces: e.g. `Analytics/RiskScoring`, `CoinMetrics/Ingestion` — use these when producing metrics.

## Code patterns & examples (what to look for)
- **SOLID Analytics Engine**: `src/analytics_engine/analytics_engine.py` uses dependency injection with protocol interfaces
  - Components: S3DataProcessor, RiskScoreCalculator, StorageManager, ReportGenerator, AnalyticsComponents (DI container)
  - Expert modules: performance_monitoring.py, circuit_breaker.py, data_validation.py, async_processing.py, error_recovery.py, config_management.py, health_checks.py
- **Common AWS patterns**: `src/common/aws_clients.py` provides centralized client factory with error handling
- **Container builds**: Shared base image pattern in `containers/base/` with function-specific `src/<name>-lambda/Dockerfile`
- **Protocol interfaces**: All major components implement protocols for testability (`@runtime_checkable` decorator)
- **CoinMetrics flow**: S3 partitioned paths `coinmetrics/year=.../month=.../day=.../<asset>_data.json`
- **Step Functions**: Three orchestration patterns in `step-functions/` (stock-tools, phase3-production, phase3-extreme-greed)

## What an AI agent should do first when editing code
1. **Run unit tests** (or the test runner) locally: `python run_tests.py --install-deps` then `python run_tests.py --lambda <name>`
2. **Check container builds**: Use `./build-containers.sh <function-name> --test` to validate container functionality
3. **Respect existing patterns**: Follow SOLID architecture in analytics_engine, use dependency injection from `src/common/`
4. **Update test coverage**: When adding lambdas, update `LAMBDA_DIRS` in `run_tests.py` (currently 19 functions listed)
5. **Follow container patterns**: Use shared base image, function-specific Dockerfiles, standardized lambda_handler signature

## CI / PR guidance (practical)
- Keep changes small and testable per-lambda. The repo expects small, independently testable Lambda changes.
- If you modify infrastructure (terraform/), include update notes in `DEPLOYMENT_GUIDE.md` and run `terraform plan` in the appropriate environment folder.
- Update `pytest.ini` markers only when you update the entire test strategy; follow existing markers (`unit`, `integration`, `slow`, `aws`).

## Quick-check examples to copy (concrete snippets)
- **Run analytics tests with coverage** (root): `python run_tests.py --lambda analytics --coverage`
- **Install deps for every lambda** (root): `python run_tests.py --install-deps`
- **Build and test container** (root): `./build-containers.sh analytics-engine --test --health-check`
- **Package fear-greed lambda** (inside folder):
  - `pip install -r requirements.txt -t .`
  - `zip -r fear-greed.zip . -x "test_*" "__pycache__/*" "*.pyc"`
- **Test all lambdas together**: `python run_tests.py --together`
- **Dashboard testing**: Function URL endpoint testing and Plotly performance validation

## When documentation is the single source
- Prefer README sections within `src/<lambda>/README.md` for per-lambda rules (these are authoritative for packaging, env vars and IAM permissions).

## Short checklist for PR reviews by an agent
- Tests: ensure `python run_tests.py` passes for affected lambda(s).
- Env vars: document new or changed env vars in the lambda README and terraform variables.
- Infra: when changing resources, include a terraform plan and note required IAM changes.
- Observability: add/update CloudWatch metrics or log keys when behavior or schema changes.

Please review these instructions and tell me which sections need more detail (examples, commands, or files to reference) so I can iterate.
