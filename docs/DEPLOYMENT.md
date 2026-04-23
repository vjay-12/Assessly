# Deployment Guide — Live URL Setup

This guide walks you through deploying the Zetheta platform to production with **live URLs**.

---

## 1. Database: Neon PostgreSQL (Cloud)

Neon is **serverless PostgreSQL** with a generous free tier (500 MB).

### Setup Steps

1. Go to **[neon.tech](https://neon.tech)** and sign up (GitHub OAuth available)
2. Click **"Create Project"**
3. Name it `zetheta-platform`
4. Neon auto-generates a password — **copy and save it**
5. In the Dashboard, go to **"Connection Details"**
6. Copy the connection string, which looks like:
   ```
   postgresql://user:password@ep-xxx.us-east-1.aws.neon.tech/zetheta?sslmode=require
   ```
7. **Convert for SQLAlchemy async** — replace `postgresql://` with `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://user:password@ep-xxx.us-east-1.aws.neon.tech/zetheta?sslmode=require
   ```

### What This Gives You
- A live PostgreSQL URL that works from **anywhere** (local Docker, Railway, Vercel)
- Auto-scaling compute
- Built-in connection pooling (PgBouncer)
- Branching (create dev/prod branches if needed)

---

## 2. Cache/Queue: Upstash Redis (Cloud)

Upstash is **serverless Redis** with a free tier (10,000 commands/day + 256 MB).

### Setup Steps

1. Go to **[console.upstash.com](https://console.upstash.com)** and sign up
2. Click **"Create Database"**
3. Name it `zetheta-redis`
4. Choose a **region close to your backend deployment** (e.g., `us-east-1` if deploying to Railway US)
5. After creation, go to the **"Redis"** tab (NOT the REST API tab)
6. Copy the **Redis URL**, which looks like:
   ```
   rediss://default:password@host.upstash.io:6379
   ```
   > Note: `rediss://` (with double `s`) means TLS/SSL enabled — required for Upstash.

### Why Upstash Over Self-Hosted Valkey?

| Feature | Upstash | Self-Hosted Valkey |
|---------|---------|-------------------|
| Setup | 1 click | Docker + networking |
| SSL/TLS | Built-in | Manual config |
| Persistence | Built-in | Configure AOF |
| Free Tier | 10k req/day + 256 MB | Only local |
| Global Edge | ✅ | ❌ |

### Code Changes Required

**None.** Upstash is 100% wire-compatible with Redis. Our Python `redis-py` client connects to Upstash using the exact same code:

```python
redis_client = redis.from_url("rediss://default:pass@host.upstash.io:6379")
```

The only difference is the connection string in `.env`.

---

## 3. Backend Deployment: Railway (Recommended)

Railway offers **$5 free credit/month** and deploys Docker containers with zero config.

### Deploy Auth Service

1. Go to **[railway.app](https://railway.app)** → New Project → Deploy from GitHub repo
2. Select your Zetheta repo
3. Add a **New Service** → Select `services/auth-service/Dockerfile`
4. In **Variables**, add:
   ```
   DATABASE_URL=postgresql+asyncpg://... (from Neon)
   REDIS_URL=rediss://default:... (from Upstash)
   JWT_SECRET=your-generated-secret
   JWT_ALGORITHM=HS256
   CROSS_APP_SECRET=your-generated-secret
   PORT=8000
   ```
5. Railway auto-assigns a URL like `https://auth-service-production.up.railway.app`

### Deploy API Gateway

1. Add another service → Select `services/api-gateway/Dockerfile`
2. In **Variables**, add:
   ```
   DATABASE_URL=postgresql+asyncpg://... (from Neon)
   REDIS_URL=rediss://default:... (from Upstash)
   JWT_SECRET=same-as-auth-service
   JWT_ALGORITHM=HS256
   AUTH_SERVICE_URL=https://auth-service-production.up.railway.app
   PORT=8000
   ```
3. Copy the Railway URL (e.g., `https://api-gateway-production.up.railway.app`)

### Deploy Evaluation Worker

1. Add another service → Select `services/evaluation-worker/Dockerfile`
2. In **Variables**, add:
   ```
   DATABASE_URL=postgresql+asyncpg://... (from Neon)
   REDIS_URL=rediss://default:... (from Upstash)
   WORKER_ID=railway-worker-1
   ```
3. **No public URL needed** — worker only talks to Valkey + Neon
4. You can scale replicas in Railway dashboard

---

## 4. Frontend Deployment: Vercel (Recommended)

Vercel deploys Next.js apps with **zero config** and gives you HTTPS URLs instantly.

### Deploy Candidate Portal

1. Go to **[vercel.com](https://vercel.com)** → Add New Project → Import GitHub repo
2. Set **Root Directory** to `apps/candidate-portal`
3. In **Environment Variables**, add:
   ```
   NEXT_PUBLIC_API_GATEWAY_URL=https://api-gateway-production.up.railway.app
   NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth-service-production.up.railway.app
   ```
4. Deploy → Vercel gives you `https://candidate-portal.vercel.app`

### Deploy Assessment Engine

1. Add another project → Root Directory: `apps/assessment-engine`
2. Environment Variables:
   ```
   NEXT_PUBLIC_API_GATEWAY_URL=https://api-gateway-production.up.railway.app
   NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth-service-production.up.railway.app
   ```
3. Deploy → `https://assessment-engine.vercel.app`

### Deploy Employer Dashboard

1. Add another project → Root Directory: `apps/employer-dashboard`
2. Environment Variables:
   ```
   NEXT_PUBLIC_API_GATEWAY_URL=https://api-gateway-production.up.railway.app
   NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth-service-production.up.railway.app
   ```
3. Deploy → `https://employer-dashboard.vercel.app`

---

## 5. Cross-App Flow in Production

In production, the cross-app redirect changes from localhost to live URLs.

### Update Candidate Portal

When "Start Assessment" is clicked, the redirect should go to the **live** Assessment Engine:

```typescript
// apps/candidate-portal/app/dashboard/page.tsx
const assessmentUrl = `https://assessment-engine.vercel.app/assessment?token=${data.token}`;
window.location.href = assessmentUrl;
```

Or better — make it dynamic via env var:
```typescript
const assessmentUrl = `${process.env.NEXT_PUBLIC_ASSESSMENT_ENGINE_URL}/assessment?token=${data.token}`;
```

### Add to Environment Variables

For **local** (`.env`):
```bash
NEXT_PUBLIC_ASSESSMENT_ENGINE_URL=http://localhost:4001
```

For **production** (Vercel env vars):
```bash
NEXT_PUBLIC_ASSESSMENT_ENGINE_URL=https://assessment-engine.vercel.app
```

---

## 6. Environment Variable Summary

### Local Development (Docker Compose)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/zetheta?sslmode=require
REDIS_URL=redis://valkey:6379          # local Valkey container
JWT_SECRET=local-secret
CROSS_APP_SECRET=local-cross-secret
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:3000
NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:3001
NEXT_PUBLIC_ASSESSMENT_ENGINE_URL=http://localhost:4001
```

### Production (Railway + Vercel + Upstash + Neon)
```bash
# Backends (Railway)
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/zetheta?sslmode=require
REDIS_URL=rediss://default:pass@host.upstash.io:6379
JWT_SECRET=production-secret-32-chars-min
CROSS_APP_SECRET=production-cross-secret-32-chars-min
AUTH_SERVICE_URL=https://auth-service-production.up.railway.app

# Frontends (Vercel)
NEXT_PUBLIC_API_GATEWAY_URL=https://api-gateway-production.up.railway.app
NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth-service-production.up.railway.app
NEXT_PUBLIC_ASSESSMENT_ENGINE_URL=https://assessment-engine.vercel.app
```

---

## 7. Verify Live Deployment

1. **Seed Neon DB locally** (one-time):
   ```bash
   cd packages/shared-db
   pip install -r requirements.txt
   export DATABASE_URL=postgresql+asyncpg://... (your Neon URL)
   python seed.py
   ```

2. **Test Candidate Flow**:
   - Open `https://candidate-portal.vercel.app`
   - Login with `alex.rivera@example.com` / `candidate123`
   - Click "Start Assessment"
   - Should redirect to `https://assessment-engine.vercel.app`
   - Complete MCQ → Submit

3. **Test Real-Time Dashboard**:
   - Open `https://employer-dashboard.vercel.app`
   - Login with `hr@zetheta.com` / `admin123`
   - "LIVE" badge should appear
   - Funnel count should auto-update when submission completes

---

## 8. Free Tier Limits (No Credit Card Needed)

| Service | Free Tier | Sufficient For? |
|---------|-----------|-----------------|
| Neon | 500 MB, unlimited connections | ✅ Yes |
| Upstash | 10k commands/day, 256 MB | ✅ Yes |
| Railway | $5/month credit | ✅ Yes (3 small services) |
| Vercel | Unlimited hobby projects | ✅ Yes |

**Total cost: $0** for the assignment demo.
