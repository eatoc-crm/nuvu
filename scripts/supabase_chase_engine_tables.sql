-- NUVU Chase Engine Phase A — run in Supabase SQL editor.
-- property_id references sales_progression.id (same as inbound_emails.property_id).

-- ── chase_messages: one row per sent chase / flag-to-team (duplicate guard) ──
CREATE TABLE IF NOT EXISTS chase_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES sales_progression (id) ON DELETE CASCADE,
  chase_stage text NOT NULL,
  chase_day integer NOT NULL DEFAULT 0,
  recipient_type text NOT NULL,
  recipient_email text,
  message_type text NOT NULL DEFAULT 'chase'
    CHECK (message_type IN ('chase', 'flag_to_team')),
  subject text,
  body_preview text,
  sent_at timestamptz,
  response_received boolean NOT NULL DEFAULT false,
  response_received_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now (),
  CONSTRAINT chase_messages_one_send_per_cadence UNIQUE (property_id, chase_stage, chase_day)
);

CREATE INDEX IF NOT EXISTS idx_chase_messages_property ON chase_messages (property_id);
CREATE INDEX IF NOT EXISTS idx_chase_messages_sent ON chase_messages (sent_at)
  WHERE sent_at IS NOT NULL;

COMMENT ON TABLE chase_messages IS
  'Phase A chase log; before send, check duplicate (property_id, chase_stage, chase_day) with sent_at set.';

-- ── chase_confirmations: inbound keyword suggestions (beta = human confirm) ──
CREATE TABLE IF NOT EXISTS chase_confirmations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES sales_progression (id) ON DELETE CASCADE,
  inbound_email_id uuid REFERENCES inbound_emails (id) ON DELETE SET NULL,
  suggested_milestone text NOT NULL,
  suggested_value timestamptz,
  email_snippet text,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'confirmed', 'dismissed')),
  confirmed_by text,
  created_at timestamptz NOT NULL DEFAULT now (),
  actioned_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_chase_confirmations_pending
  ON chase_confirmations (status, created_at DESC)
  WHERE status = 'pending';

COMMENT ON TABLE chase_confirmations IS
  'Inbound email milestone suggestions; dashboard Confirm/Dismiss before updating sales_progression.';

-- ── preferred_surveyors: agency panel for survey Day 3 copy (may already exist) ──
CREATE TABLE IF NOT EXISTS preferred_surveyors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id text NOT NULL DEFAULT 'dbe',
  surveyor_name text,
  surveyor_firm text,
  contact_email text,
  contact_phone text,
  coverage_area text,
  google_rating numeric,
  created_at timestamptz NOT NULL DEFAULT now ()
);

CREATE INDEX IF NOT EXISTS idx_preferred_surveyors_agency
  ON preferred_surveyors (agency_id);

COMMENT ON TABLE preferred_surveyors IS
  'Agency-specific surveyor recommendations (Progression Engine spec §5.2).';
