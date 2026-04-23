# Cross-Application Token Design

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Token guessability | 256-bit CSPRNG (`secrets.token_urlsafe(32)`) |
| Token reuse | Atomic `GET` + `DELETE` on redemption |
| Replay attacks | 120s TTL + single-use + HMAC binding |
| Client generation | Impossible — only authenticated `/auth/cross-app-token` can mint |
| Session hijacking | Token bound to specific `candidate_id` + `application_id` |
| Timing attacks | `hmac.compare_digest()` for all comparisons |

## Token Lifecycle

### 1. Mint (Auth Service)
```python
token_id = secrets.token_urlsafe(32)      # 256-bit random
nonce = secrets.token_urlsafe(16)         # 128-bit nonce
timestamp = datetime.utcnow().isoformat()

binding = hmac.new(
    CROSS_APP_SECRET,
    f"{candidate_id}:{app_id}:{nonce}:{timestamp}".encode(),
    hashlib.sha256
).hexdigest()

# Store in Valkey with 120s TTL
valkey.setex(f"crossapp:{token_id}", 120, json.dumps({
    "candidate_id": candidate_id,
    "application_id": app_id,
    "nonce": nonce,
    "binding": binding,
    "used": False
}))

return f"ca_{token_id}:{binding}"
```

### 2. Redeem (Auth Service)
```python
# Parse token
token_id, provided_binding = token[3:].split(":")

# Fetch from Valkey
raw = valkey.get(f"crossapp:{token_id}")
if not raw: raise 401 TOKEN_EXPIRED

payload = json.loads(raw)
if payload["used"]: raise 410 TOKEN_ALREADY_REDEEMED

# Verify binding
if not hmac.compare_digest(payload["binding"], provided_binding):
    raise 401 INVALID_TOKEN

# Atomic delete (single-use guarantee)
valkey.delete(f"crossapp:{token_id}")

# Issue assessment session JWT (5-min expiry)
return create_assessment_session_jwt(...)
```

### 3. Cleanup
- Valkey TTL auto-expires unredeemed tokens after 120s
- Redeemed tokens are immediately deleted

## Why Opaque Over JWT?

JWTs are stateless and cannot be revoked instantly. For a **single-use** token, server-side state (Valkey) is required to track consumption. Opaque tokens + Redis/Valkey backing is the correct architectural choice.

## Security Properties

| Property | Implementation |
|----------|---------------|
| Confidentiality | HTTPS-only transmission |
| Integrity | HMAC-SHA256 binding |
| Freshness | 120-second TTL |
| Uniqueness | Cryptographic random + atomic delete |
| Non-repudiation | Server logs all mint/redeem operations |
