-- ============================================================================
-- ZETHETA ASSIGNMENT - PostgreSQL Database Schema
-- Database: assessly
-- Created: April 27, 2026
-- ============================================================================

-- ============================================================================
-- ENUMS - Define all enumerated types
-- ============================================================================

CREATE TYPE user_role AS ENUM ('candidate', 'admin');
CREATE TYPE difficulty_level AS ENUM ('Easy', 'Medium', 'Hard');
CREATE TYPE enrollment_status AS ENUM ('Assigned', 'In Progress', 'Completed', 'Failed', 'In Review');
CREATE TYPE application_status AS ENUM ('applied', 'attempted', 'submitted', 'evaluated');
CREATE TYPE severity_level AS ENUM ('Informational', 'Medium', 'High', 'Critical');
CREATE TYPE audit_event_type AS ENUM (
    'LOGIN',
    'LOGOUT',
    'ASSESSMENT_STARTED',
    'ASSESSMENT_SUBMITTED',
    'ANSWER_SAVED',
    'SESSION_EXPIRED',
    'TOKEN_ISSUED',
    'TOKEN_USED',
    'TOKEN_INVALIDATED',
    'PERMISSION_CHANGE',
    'RESULT_OVERRIDE',
    'PAGE_VISITED'
);

-- ============================================================================
-- TABLE: users
-- Purpose: User accounts for both candidates and administrators
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'candidate',
    avatar_url VARCHAR(500),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_role_created ON users(role, created_at);

COMMENT ON TABLE users IS 'Stores user accounts (candidates and admins)';
COMMENT ON COLUMN users.id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN users.email IS 'Unique email address';
COMMENT ON COLUMN users.role IS 'User role: candidate or admin';
COMMENT ON COLUMN users.is_deleted IS 'Soft delete flag';

-- ============================================================================
-- TABLE: assessments
-- Purpose: Assessment templates/configurations
-- ============================================================================
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    difficulty difficulty_level NOT NULL,
    duration_minutes INTEGER NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    pass_mark INTEGER NOT NULL DEFAULT 50,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_assessments_category ON assessments(category);
CREATE INDEX ix_assessments_is_published ON assessments(is_published);

COMMENT ON TABLE assessments IS 'Assessment configurations and templates';
COMMENT ON COLUMN assessments.created_by IS 'Admin who created the assessment';
COMMENT ON COLUMN assessments.pass_mark IS 'Minimum percentage to pass (default 50%)';

-- ============================================================================
-- TABLE: questions
-- Purpose: MCQ question bank for assessments
-- ============================================================================
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    code_snippet TEXT,
    options TEXT[] NOT NULL,
    correct_option INTEGER NOT NULL,
    points INTEGER NOT NULL DEFAULT 1,
    difficulty INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_questions_assessment ON questions(assessment_id);
CREATE INDEX ix_questions_difficulty ON questions(difficulty);

COMMENT ON TABLE questions IS 'Multiple choice questions with 4 options';
COMMENT ON COLUMN questions.options IS 'PostgreSQL array of 4 answer options';
COMMENT ON COLUMN questions.correct_option IS 'Zero-based index of correct answer (0-3)';
COMMENT ON COLUMN questions.code_snippet IS 'Optional code snippet for coding questions';

-- ============================================================================
-- TABLE: assessment_assignments
-- Purpose: Links candidates to assigned assessments
-- ============================================================================
CREATE TABLE assessment_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    due_at TIMESTAMPTZ,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_assignments_candidate ON assessment_assignments(candidate_id);
CREATE INDEX ix_assignments_assessment ON assessment_assignments(assessment_id);
CREATE UNIQUE INDEX ix_assignments_candidate_assessment ON assessment_assignments(candidate_id, assessment_id);

COMMENT ON TABLE assessment_assignments IS 'Assignment of assessments to candidates';
COMMENT ON COLUMN assessment_assignments.due_at IS 'Deadline for completing the assessment';

-- ============================================================================
-- TABLE: test_sessions
-- Purpose: Records of assessment attempts by candidates
-- ============================================================================
CREATE TABLE test_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    status enrollment_status NOT NULL DEFAULT 'Assigned',
    application_status application_status NOT NULL DEFAULT 'applied',
    score_percentage FLOAT,
    total_questions INTEGER,
    correct_count INTEGER,
    total_answered INTEGER NOT NULL DEFAULT 0,
    time_taken_seconds INTEGER,
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    evaluated_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    worker_id VARCHAR(100),
    proctor_log_url VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_sessions_candidate ON test_sessions(candidate_id);
CREATE INDEX ix_sessions_assessment ON test_sessions(assessment_id);
CREATE INDEX ix_sessions_status ON test_sessions(status);
CREATE INDEX ix_sessions_app_status ON test_sessions(application_status);
CREATE INDEX ix_sessions_evaluated ON test_sessions(evaluated_at);
CREATE INDEX ix_sessions_submitted ON test_sessions(submitted_at);

COMMENT ON TABLE test_sessions IS 'Assessment attempt records with scoring and timing';
COMMENT ON COLUMN test_sessions.status IS 'Enrollment status (Assigned, In Progress, Completed, Failed, In Review)';
COMMENT ON COLUMN test_sessions.application_status IS 'Pipeline status (applied, attempted, submitted, evaluated)';
COMMENT ON COLUMN test_sessions.worker_id IS 'ID of the evaluation worker for observability';

-- ============================================================================
-- TABLE: session_responses
-- Purpose: Individual question answers for each test session
-- ============================================================================
CREATE TABLE session_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_option INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    flagged BOOLEAN NOT NULL DEFAULT FALSE,
    time_spent_seconds INTEGER,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_responses_session ON session_responses(session_id);
CREATE INDEX ix_responses_question ON session_responses(question_id);
CREATE UNIQUE INDEX ix_responses_session_question ON session_responses(session_id, question_id);

COMMENT ON TABLE session_responses IS 'Answer records for each question in a session';
COMMENT ON COLUMN session_responses.selected_option IS 'Zero-based index of selected answer (0-3)';
COMMENT ON COLUMN session_responses.flagged IS 'Whether candidate marked for review';
COMMENT ON COLUMN session_responses.is_correct IS 'Auto-populated after evaluation';

-- ============================================================================
-- TABLE: otp_tokens
-- Purpose: One-time passwords for multi-factor authentication
-- ============================================================================
CREATE TABLE otp_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES test_sessions(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    ip_address VARCHAR(45)
);

CREATE INDEX ix_otp_token_hash ON otp_tokens(token_hash);
CREATE INDEX ix_otp_user_used ON otp_tokens(user_id, is_used);
CREATE INDEX ix_otp_expires ON otp_tokens(expires_at);

COMMENT ON TABLE otp_tokens IS 'One-time passwords for 2FA';
COMMENT ON COLUMN otp_tokens.session_id IS 'Associated test session (if applicable)';
COMMENT ON COLUMN otp_tokens.token_hash IS 'Hash of the OTP for security';

-- ============================================================================
-- TABLE: refresh_tokens
-- Purpose: JWT refresh tokens for session management
-- ============================================================================
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_refresh_token_hash ON refresh_tokens(token_hash);
CREATE INDEX ix_refresh_user ON refresh_tokens(user_id, is_revoked);
CREATE INDEX ix_refresh_expires ON refresh_tokens(expires_at);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for authentication';
COMMENT ON COLUMN refresh_tokens.is_revoked IS 'Revocation flag for token invalidation';

-- ============================================================================
-- TABLE: pending_evaluations
-- Purpose: Recovery queue for failed evaluation scenarios
-- ============================================================================
CREATE TABLE pending_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_pending_session ON pending_evaluations(session_id);
CREATE INDEX ix_pending_queued ON pending_evaluations(queued_at);

COMMENT ON TABLE pending_evaluations IS 'Recovery table for Redis/Valkey downtime scenarios';
COMMENT ON COLUMN pending_evaluations.session_id IS 'Session pending evaluation';

-- ============================================================================
-- TABLE: audit_logs
-- Purpose: Security and activity audit trail
-- ============================================================================
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type audit_event_type NOT NULL,
    severity severity_level NOT NULL DEFAULT 'Informational',
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_audit_user ON audit_logs(user_id);
CREATE INDEX ix_audit_event_type ON audit_logs(event_type);
CREATE INDEX ix_audit_severity ON audit_logs(severity);
CREATE INDEX ix_audit_created ON audit_logs(created_at);

COMMENT ON TABLE audit_logs IS 'Complete activity audit trail with 12 event types';
COMMENT ON COLUMN audit_logs.event_type IS 'Type of event (LOGIN, LOGOUT, ASSESSMENT_STARTED, etc.)';
COMMENT ON COLUMN audit_logs.severity IS 'Severity level (Informational, Medium, High, Critical)';

-- ============================================================================
-- TABLE: department_benchmarks
-- Purpose: Analytics and performance metrics by category
-- ============================================================================
CREATE TABLE department_benchmarks (
    category VARCHAR(100) PRIMARY KEY,
    avg_score FLOAT,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    pass_rate FLOAT,
    top_skills TEXT[],
    last_updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE department_benchmarks IS 'Performance benchmarks and analytics by assessment category';
COMMENT ON COLUMN department_benchmarks.top_skills IS 'Array of top performing skill areas';
COMMENT ON COLUMN department_benchmarks.pass_rate IS 'Overall pass rate percentage for category';

-- ============================================================================
-- FOREIGN KEY RELATIONSHIPS SUMMARY
-- ============================================================================
-- users (1) ──→ (N) assessment_assignments
-- users (1) ──→ (N) test_sessions
-- users (1) ──→ (N) otp_tokens
-- users (1) ──→ (N) refresh_tokens
-- users (1) ──→ (N) audit_logs
-- 
-- assessments (1) ──→ (N) questions
-- assessments (1) ──→ (N) assessment_assignments
-- assessments (1) ──→ (N) test_sessions
-- 
-- questions (1) ──→ (N) session_responses
-- 
-- test_sessions (1) ──→ (N) session_responses
-- test_sessions (1) ──→ (1) pending_evaluations
-- test_sessions (1) ──→ (N) otp_tokens

-- ============================================================================
-- TRIGGERS - Automatically update updated_at timestamps
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assessments_updated_at BEFORE UPDATE ON assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA (Optional - Comment out if not needed)
-- ============================================================================

-- Insert sample admin user
INSERT INTO users (email, full_name, password_hash, role, is_verified)
VALUES (
    'admin@assessly.com',
    'Admin User',
    '$2b$12$...',  -- Replace with actual bcrypt hash
    'admin',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Insert sample assessment
INSERT INTO assessments (title, description, category, difficulty, duration_minutes, total_questions, pass_mark, is_published)
VALUES (
    'Python Fundamentals Assessment',
    'Assess Python programming basics and fundamentals',
    'Python',
    'Medium',
    60,
    20,
    50,
    TRUE
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF SCHEMA DEFINITION
-- ============================================================================
