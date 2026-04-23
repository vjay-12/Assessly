# API Design Document

## Auth Service (`auth-service:8000`)

### POST /auth/login
Candidate or employer login.

**Request:**
```json
{
  "email": "alex.rivera@example.com",
  "password": "candidate123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /auth/cross-app-token
Mints a short-lived opaque token for cross-application flow.

**Headers:** `Authorization: Bearer <JWT>`

**Request:**
```json
{
  "application_id": "uuid"
}
```

**Response 201:**
```json
{
  "token": "ca_abc123...",
  "expires_at": "2026-04-23T20:19:00Z",
  "expires_in": 120
}
```

### POST /auth/redeem-cross-app
Redeems opaque token for an assessment session JWT.

**Request:**
```json
{
  "token": "ca_abc123..."
}
```

**Response 200:**
```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIs...",
  "candidate_id": "uuid",
  "application_id": "uuid"
}
```

**Errors:**
- `401 TOKEN_EXPIRED` — token not found in Valkey
- `410 TOKEN_ALREADY_REDEEMED` — token was already used

### GET /auth/verify
Verifies any JWT token.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "valid": true,
  "user_id": "uuid",
  "role": "candidate"
}
```

## API Gateway (`api-gateway:8000`)

### GET /api/questions
Fetches MCQ questions for the assessment.

**Auth:** Assessment session JWT

**Response 200:**
```json
[
  {
    "id": "uuid",
    "question_text": "What is...?",
    "options": ["A", "B", "C", "D"],
    "difficulty": 1
  }
]
```

### POST /api/submissions
Submits assessment answers and triggers async evaluation.

**Auth:** Assessment session JWT

**Request:**
```json
{
  "application_id": "uuid",
  "answers": [
    { "question_id": "uuid", "selected_option": 1 },
    { "question_id": "uuid", "selected_option": 0 }
  ]
}
```

**Response 202:**
```json
{
  "status": "submitted",
  "application_id": "uuid",
  "message": "Assessment submitted successfully. Evaluation in progress."
}
```

### GET /api/candidates
Lists candidates with filters.

**Auth:** Employer JWT

**Query Params:**
- `status` — filter by candidate status
- `search` — name/email search
- `limit` — pagination (default 50)
- `offset` — pagination (default 0)

### GET /api/scores
Lists evaluation scores.

**Auth:** Employer JWT

**Query Params:**
- `min_score` — minimum percentage
- `limit`, `offset` — pagination

### GET /api/analytics/funnel
Returns funnel stage counts.

**Auth:** Employer JWT

**Response 200:**
```json
{
  "applied": 1284,
  "attempted": 856,
  "submitted": 712,
  "evaluated": 680
}
```

### GET /api/events
Server-Sent Events stream for real-time updates.

**Auth:** Employer JWT (via header)

**Stream Format:**
```
data: {"type": "EVALUATION_COMPLETED", "payload": {"application_id": "...", "percentage": 84}}
```
