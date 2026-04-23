# Deployment Design

## Local Development (Docker Compose)

```yaml
services:
  valkey:           # Cache + Queue
  auth-service:     # Port 3001
  api-gateway:      # Port 3000
  evaluation-worker: # 1 replica (scalable)
  candidate-portal:  # Port 4000
  assessment-engine: # Port 4001
  employer-dashboard: # Port 4002
```

All services start with: `docker compose up --build`

## Service Dependencies

```
valkey ←── auth-service, api-gateway, evaluation-worker
neon-db ←── auth-service, api-gateway, evaluation-worker
auth-service ←── api-gateway (for JWT verification delegation)
```

## Health Checks

| Service | Endpoint | Interval |
|---------|----------|----------|
| valkey | `valkey-cli ping` | 5s |
| auth-service | `GET /health` | 10s |
| api-gateway | `GET /health` | 10s |

## Environment Variables

All secrets are injected via `.env` (never committed):
- `DATABASE_URL` — Neon PostgreSQL connection
- `REDIS_URL` — Valkey connection
- `JWT_SECRET` — Shared across services for JWT verification
- `CROSS_APP_SECRET` — HMAC key for cross-app tokens

## Non-Root Containers

All Dockerfiles create `appuser` (UID 1001) and run services under that user:
```dockerfile
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
USER appuser
```

## Cloud Deployment (Bonus)

| Component | Platform |
|-----------|----------|
| Frontends | Vercel |
| Backend Services | Railway / Render |
| Database | Neon (already cloud) |
| Cache/Queue | Self-hosted Valkey on Railway |

## Scaling Considerations

- **API Gateway**: Stateless — scale horizontally behind a load balancer
- **Auth Service**: Stateless — scale horizontally
- **Evaluation Worker**: Scale replicas independently; all workers consume from same queue
- **Valkey**: For production, use clustered Valkey or AWS ElastiCache for Valkey
- **Neon**: Auto-scales compute; connection pooling via PgBouncer handles burst traffic
