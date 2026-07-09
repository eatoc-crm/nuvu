-- NUVU Phase 0.3 — durable notification send-once log.
-- Queue rows are disposable; this table is the permanent send memory.

CREATE TABLE IF NOT EXISTS notification_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id TEXT NOT NULL DEFAULT 'dbe',
  property_address TEXT NOT NULL,
  notification_type TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  recipient TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_notif_log_lookup
  ON notification_log (agency_id, property_address, notification_type, content_hash);

CREATE INDEX IF NOT EXISTS idx_notif_log_sent_at
  ON notification_log (sent_at);

ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE notification_log IS
  'Append-only send-once memory for NUVU notifications; survives intake_queue rebuilds.';
