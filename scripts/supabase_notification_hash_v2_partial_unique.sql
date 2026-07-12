-- Brief A / Amendment 1: reserve-before-send race guard for new notification rows.
-- Historical notification_log duplicates are preserved; uniqueness applies only
-- to rows created from 2026-07-12 onward.

CREATE UNIQUE INDEX IF NOT EXISTS uniq_notification_hash_v2
  ON notification_log (agency_id, content_hash)
  WHERE sent_at >= '2026-07-12T00:00:00Z';
