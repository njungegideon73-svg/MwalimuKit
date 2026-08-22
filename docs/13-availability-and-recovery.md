# 13 — Availability, Recovery, & Observability

## Overview

This document describes how MwalimuKit maintains availability, how it
recovers from failures, and how operators are alerted.  It maps to the
**"Availability and recovery"** layer of the production stack.

## Current implementation status

| Capability                | Status      | Where                                               |
| ------------------------- | ----------- | --------------------------------------------------- |
| Health / liveness probe   | Implemented | `api/app/routers/health.py` — `/health`             |
| Readiness probe           | Implemented | `/ready` — checks DB + Redis                    |
| Container restart policy  | Implemented | `docker-compose.yml` — `unless-stopped`         |
| Nightly DB backups        | Implemented | `docker-compose.yml` profile `backup` + `scripts/backup.sh` |
| Point-in-time restore     | Implemented | `scripts/restore.sh`                              |
| Multi-AZ database         | Terraform   | `infra/terraform/main.tf` — `module.rds.multi_az` |
| Automated fail-over       | Terraform   | RDS Multi-AZ (managed by AWS)                 |
| Connection draining       | Terraform   | ALB target groups with health checks            |
| Prometheus metrics        | Implemented | `api/app/core/metrics.py` + `/metrics`       |
| Structured logging        | Implemented | `api/app/core/logging.py` (structlog JSON)  |
| Error tracking (Sentry)   | Implemented | `api/app/core/sentry.py`                      |
| Alert rules               | Implemented | `infra/monitoring/prometheus/alerts.yml`    |
| Alert routing             | Implemented | `infra/monitoring/prometheus/alertmanager.yml` |
| Grafana dashboards        | Implemented | `infra/monitoring/grafana/provisioning/...` |
| Runbook                   | This doc    | §2–§4 below                                      |

---

## 1 — Health checks

### Liveness: `GET /health`
Returns `{"status":"ok"}` with no external dependencies.  Used by:
- Docker container healthchecks
- Fly.io `[[http_service.checks]]`
- Kubernetes/Docker liveness probes

### Readiness: `GET /ready`
Checks:
1. **Database** — executes `SELECT 1` against Postgres.  Returns `503`
   when the DB is unreachable, draining traffic from the LB.
2. **Redis** — pings Redis; reports `"ok"`, `"degraded"`, or
   `"not configured"`.  Redis is optional (the rate limiter degrades
   to in-process), so its failure alone does **not** cause 503.

### Container healthchecks
Both the API and Web containers define healthchecks in their Dockerfiles.
The nginx load balancer and ALB use `/health` (API) and `/` (Web).

---

## 2 — Backups & Restore

### Automated nightly backups (Docker Compose)
The `db-backup` service is started on demand:

```bash
docker compose --profile backup up -d db-backup
```

It dumps the database in custom format (`.dump.gz`), retains backups for
`RETENTION_DAYS` (default 14), and validates each dump with `gunzip -t`
and a `PGDMP` magic-byte check.

### Manual backup
```bash
./scripts/backup.sh
```

### Restore
```bash
./scripts/restore.sh backups/mwalimukit-20260822T000000Z.dump.gz
```

The restore script:
1. Stops the API and Web containers
2. Terminates active DB connections
3. Drops and recreates the database
4. Restores from the dump
5. Restarts services

### AWS (Terraform)
RDS automated backups are enabled with a 14-day retention window and a
daily snapshot window at `02:00–03:00 UTC`.  Final snapshots are taken
on destroy.  Point-in-time recovery is supported via the AWS Console or
`aws rds restore-db-instance-to-point-in-time`.

---

## 3 — Disaster Recovery Plan

### RTO / RPO
| Metric        | Target                       |
| ------------- | ----------------------------- |
| **RTO**       | 4 hours (data restore)        |
| **RPO**       | 24 hours (nightly backup)     |
| **RTO**       | 30 minutes (failover) for HA DB (Terraform/AWS) |
| **RPO**       | 5 minutes (PITR) for AWS RDS  |

### Recovery scenarios

#### Scenario A: Single AZ failure (AWS)
1. RDS Multi-AZ automatically promotes the standby.
2. ECS services reconnect to the new primary endpoint (unchanged DNS).
3. No data loss (synchronous replication).
4. Alert fires: `DBUnhealthy` → resolved automatically.

#### Scenario B: Full region outage (AWS)
1. Promote the latest RDS snapshot to a new cluster in the backup region.
2. Update DNS (Route 53) to point to the new ALB.
3. Deploy the latest Docker images to the backup region's ECS cluster.
4. Restore Redis from the latest backup (if AOF persistence is enabled)
   or accept cache cold-start.

#### Scenario C: Application bug corrupts data
1. Identify the timeframe of corruption from `activity_logs`.
2. Restore from the nearest clean backup (before the bug).
3. Re-apply migrations (`alembic upgrade head`).
4. Re-seed curriculum data.

#### Scenario D: Lost JWT secret (dev / staging)
1. Generate a new `API_SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Update the secret in the environment / secret manager.
3. All existing sessions are invalidated (token_version mismatch).
4. Users must re-authenticate.

### Testing the recovery plan
- Monthly: restore the latest backup to a staging DB and run the test
  suite against it.
- Quarterly: `terraform destroy`/`terraform apply` to a staging
  environment to verify the full IaC can be rebuilt.

---

## 4 — Load balancing, scaling & failover

### Docker Compose (single-node)
- **nginx** reverse proxy distributes API requests across N gunicorn
  workers (``API_WORKERS``, default 4).
- Health checks on `/health` drive nginx upstream availability.
- The `db-backup` service runs on the `backup` profile.

### Cloud (Terraform / AWS)
- **ALB** terminates TLS and routes to ECS Fargate target groups.
- **Auto Scaling** via Application Auto Scaling:
  - Scale-out: CPU > 70% for 60 s → add 1 task (max 5).
  - Scale-in: CPU < 40% for 300 s → remove 1 task (min 1).
- **RDS Multi-AZ**: automatic failover within the region.
- **ElastiCache Redis**: single-node (cache tier; rate limiting
  degrades gracefully without it).

### Zero-downtime deploys
```bash
./scripts/deploy.sh production apply
```
Uses `docker compose up --no-deps` so new containers start before old
ones are removed, with nginx continuing to route to healthy upstreams.

### Graceful shutdown
Both Dockerfiles define `STOPSIGNAL SIGTERM` handling.  Uvicorn and
gunicorn receive SIGTERM, finish in-flight requests (with a 30 s
timeout), then exit.  The ALB target group drains connections for 60 s
before sending SIGKILL.

---

## 5 — Monitoring stack

Run locally:
```bash
docker compose -f infra/docker-compose.yml \
  -f infra/monitoring/docker-compose.monitoring.yml up -d
```

| Component     | Port | Purpose                               |
| ------------- | ---- | ------------------------------------- |
| Prometheus    | 9090 | Metrics collection + alert evaluation |
| Grafana       | 3001 | Dashboards (admin/admin)              |
| Alertmanager  | 9093 | Alert routing + deduplication         |

### Key metrics (exposed at `/metrics`)
- `mwalimukit_http_requests_total` — per-route, per-status counters
- `mwalimukit_http_request_duration_seconds` — p50/p95/p99 latency
- `mwalimukit_rate_limited_total` — rate-limited requests
- `mwalimukit_login_failures_total` — auth security events
- `mwalimukit_lockouts_total` — account lockouts
- `mwalimukit_oversized_requests_total` — body-size rejections
- `mwalimukit_uptime_seconds` — process uptime

### Alert rules (summary)
See `infra/monitoring/prometheus/alerts.yml` for the full list.
Key alerts:
- **APIHighErrorRate** — >5% 5xx over 2 min → critical
- **APIHighLatency** — p95 > 2 s over 3 min → warning
- **APIUnhealthy** — endpoint disappears from Prometheus → critical
- **DBUnavailable** — Postgres unreachable → critical
- **RedisUnavailable** — Redis unreachable → critical
- **DiskSpaceCritical** — root fs < 10% → critical
- **HighCPUUsage** — host CPU > 80% → warning

---

## 6 — Log aggregation

The API emits structured JSON to stdout (via `structlog`), which Docker
captures and CloudWatch/ECS collects automatically in AWS.  For
self-hosted deployments, a lightweight `docker logs` pipeline or
[vector](https://vector.dev) forwarder can ship logs to a central store:

```bash
# Quick local log tail
docker compose logs -f api --tail=100
```

### Log fields (structured)
| Field          | Description                              |
| -------------- | ---------------------------------------- |
| `request_id`   | Per-request UUID (correlates all logs)  |
| `method`       | HTTP method                              |
| `path`         | Request path                             |
| `status`       | HTTP status code                         |
| `duration_ms`  | Request duration                         |
| `ip`           | Client IP (truncated / privacy-safe)    |
| `error`        | Exception type (on 5xx)                  |
| `detail`       | Error detail (on 5xx, no stack trace)   |

### Privacy
Request bodies are never logged.  On validation errors, the echoed input
is stripped (see `RequestValidationError` handler in `main.py`).
