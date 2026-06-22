-- Stage 1: Completeness Gate — intake_queue table
-- Applied: 2026-06-22
-- Run once on the NUVU Supabase project (xhxgqbjrgqyrrazmvufh)

CREATE TABLE IF NOT EXISTS intake_queue (
  id                UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  property_address  TEXT        NOT NULL,
  gate_status       TEXT        NOT NULL CHECK (gate_status IN ('blocked', 'ready', 'approved', 'rejected')),
  tier_1a_pass      BOOLEAN     NOT NULL DEFAULT false,
  tier_1b_pass      BOOLEAN     NOT NULL DEFAULT false,
  tier_1c_pass      BOOLEAN     NOT NULL DEFAULT false,
  tier_1d_pass      BOOLEAN     NOT NULL DEFAULT false,
  missing_fields    JSONB,
  sale_price        NUMERIC,
  completion_target TEXT,
  special_conditions TEXT,
  approved_by       TEXT,
  approved_at       TIMESTAMPTZ,
  notification_sent BOOLEAN     NOT NULL DEFAULT false,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS intake_queue_property_address_key ON intake_queue (property_address);
CREATE INDEX IF NOT EXISTS intake_queue_gate_status_idx             ON intake_queue (gate_status);
CREATE INDEX IF NOT EXISTS intake_queue_created_at_idx              ON intake_queue (created_at);
