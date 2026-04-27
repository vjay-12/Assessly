-- Create audit_logs table with all columns
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'Informational',
    details TEXT,
    assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS ix_audit_category ON audit_logs(category);
CREATE INDEX IF NOT EXISTS ix_audit_severity ON audit_logs(severity);
CREATE INDEX IF NOT EXISTS ix_audit_assessment ON audit_logs(assessment_id);
CREATE INDEX IF NOT EXISTS ix_audit_created ON audit_logs(created_at);
