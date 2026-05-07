-- Window 3: run in Supabase SQL editor (or migration) before using PDF dispatch.
-- Adjust if portal_sessions uses a different name or FK.

CREATE TABLE IF NOT EXISTS form_completions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES portal_sessions (id) ON DELETE CASCADE,
  property_address text NOT NULL,
  form_type text NOT NULL CHECK (form_type IN ('ta6', 'ta10')),
  status text NOT NULL DEFAULT 'in_progress',
  questions_answered integer NOT NULL DEFAULT 0,
  questions_total integer NOT NULL DEFAULT 0,
  pdf_path text,
  reviewed_by text,
  reviewed_at timestamptz,
  dispatched_at timestamptz,
  dispatched_to text,
  CONSTRAINT form_completions_session_id_key UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS form_completions_property_address_idx
  ON form_completions (property_address);

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS protocol_forms_returned timestamptz;

COMMENT ON COLUMN sales_progression.protocol_forms_returned IS
  'Set when TA6/TA10 is dispatched to solicitor (augment only; never overwrite).';
