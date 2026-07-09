-- NUVU Phase 0.4 — global outbound send governor log.
-- Records every governed_send() attempt, including blocked attempts.

CREATE TABLE IF NOT EXISTS send_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id TEXT NOT NULL DEFAULT 'dbe',
  category TEXT NOT NULL,
  recipient TEXT NOT NULL,
  subject TEXT,
  outcome TEXT NOT NULL,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_send_log_window
  ON send_log (agency_id, attempted_at);

CREATE INDEX IF NOT EXISTS idx_send_log_category
  ON send_log (category, attempted_at);

ALTER TABLE send_log ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE send_log IS
  'Append-only global email governor log for sent and blocked outbound attempts.';
