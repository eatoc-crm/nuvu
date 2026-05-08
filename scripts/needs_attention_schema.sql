-- NUVU Needs Attention + dashboard pipeline fields (run in Supabase SQL editor).

-- 3.1 Local authority expected search turnaround (no hardcoding in app)
CREATE TABLE IF NOT EXISTS local_authority_search_times (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  local_authority_name text NOT NULL UNIQUE,
  avg_turnaround_days integer NOT NULL,
  last_updated timestamptz NOT NULL DEFAULT now(),
  updated_by text
);

COMMENT ON TABLE local_authority_search_times IS
  'Expected local authority search turnaround; used by Needs Attention trigger 6.';

-- 3.2 Preferred surveyors (agency-scoped)
CREATE TABLE IF NOT EXISTS preferred_surveyors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id text NOT NULL DEFAULT 'dbe',
  surveyor_name text NOT NULL,
  surveyor_firm text,
  contact_email text,
  contact_phone text,
  coverage_area text,
  google_rating numeric(2,1)
);

CREATE INDEX IF NOT EXISTS preferred_surveyors_agency_id_idx
  ON preferred_surveyors (agency_id);

-- 3.3 sales_pipeline
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS chain_status text DEFAULT 'stable';

ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS local_authority text;

COMMENT ON COLUMN sales_pipeline.chain_status IS
  'Manual: stable | at_risk | broken (Needs Attention trigger 8).';

-- sales_progression: seller TA6/TA10 dispatch timestamp (buyer stays on protocol_forms_returned)
ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS seller_forms_returned timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS welcome_emails_sent timestamptz;

COMMENT ON COLUMN sales_progression.seller_forms_returned IS
  'When seller TA6/TA10 dispatched to solicitor (portal); buyer protocol uses protocol_forms_returned.';

COMMENT ON COLUMN sales_progression.welcome_emails_sent IS
  'Optional anchor for protocol/survey triggers; falls back to memo_sent in app if null.';
