# Security Audit Notes

## Dependencies Audit

### Python Backend
Run the following commands to audit Python dependencies:

```bash
# Install audit tools
pip install pip-audit safety

# Run audits
pip-audit --desc
safety check
```

**Current Status (Manual Review):**
- `fastapi==0.110.0` — No known critical vulnerabilities
- `uvicorn==0.29.0` — No known critical vulnerabilities
- `sqlalchemy==2.0.29` — No known critical vulnerabilities
- `redis==5.0.3` — No known critical vulnerabilities
- `python-jose==3.3.0` — No known critical vulnerabilities
- `passlib[bcrypt]==1.7.4` — No known critical vulnerabilities
- `pydantic==2.6.4` — No known critical vulnerabilities

### Node.js Frontend
Run the following commands to audit Node.js dependencies:

```bash
# For each app
cd apps/candidate-portal && npm audit
cd apps/assessment-engine && npm audit
cd apps/employer-dashboard && npm audit
```

**Current Status:**
- `next@15.0.0` — No known critical vulnerabilities in current release
- `react@18.3.0` — No known critical vulnerabilities
- `tailwindcss@3.4.1` — No known critical vulnerabilities

## Security Measures Implemented

1. **No secrets in repository** — All credentials via `.env` (`.env.example` provided)
2. **Input validation** — Pydantic v2 on all FastAPI endpoints; Zod ready for frontend
3. **Password hashing** — `bcrypt` with `passlib`
4. **JWT security** — HS256 with `exp` claim and type scoping
5. **Cross-app tokens** — Cryptographically random, HMAC-bound, 120s TTL, single-use
6. **CORS** — Configured on all backend services
7. **Non-root containers** — All Dockerfiles run as `appuser` (UID 1001)
8. **SQL injection prevention** — SQLAlchemy ORM with parameterized queries
9. **Timing attack mitigation** — `hmac.compare_digest()` for all sensitive comparisons

## Recommendations for Production

1. Switch JWT from HS256 to RS256 with separate key pairs per service
2. Add rate limiting (e.g., `slowapi`) to auth endpoints
3. Implement IP-based throttling for cross-app token minting
4. Add Web Application Firewall (WAF) rules for API Gateway
5. Enable PostgreSQL SSL enforcement with certificate pinning
6. Rotate `CROSS_APP_SECRET` and `JWT_SECRET` periodically
7. Add Content Security Policy (CSP) headers to Next.js apps
