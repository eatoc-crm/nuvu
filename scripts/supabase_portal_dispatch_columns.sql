-- Portal dispatch (send magic link + seller submit). Run in Supabase SQL editor.
-- Safe to re-run: uses IF NOT EXISTS patterns where supported.

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS token text;

CREATE UNIQUE INDEX IF NOT EXISTS portal_sessions_token_key
  ON portal_sessions (token)
  WHERE token IS NOT NULL AND length(trim(token)) > 0;

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS property_id uuid REFERENCES sales_pipeline (id);

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS seller_email text;

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft';

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS submitted_at timestamptz;

ALTER TABLE portal_sessions
  ADD COLUMN IF NOT EXISTS link_sent_at timestamptz;

-- Allow combined seller flow in addition to single-form sessions.
ALTER TABLE portal_sessions DROP CONSTRAINT IF EXISTS portal_sessions_form_type_check;
ALTER TABLE portal_sessions
  ADD CONSTRAINT portal_sessions_form_type_check
  CHECK (form_type IN ('ta6', 'ta10', 'ta6_ta10'));

-- Only when Window 3 form_completions table exists (some environments omit it).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'form_completions'
  ) THEN
    ALTER TABLE form_completions DROP CONSTRAINT IF EXISTS form_completions_form_type_check;
    ALTER TABLE form_completions
      ADD CONSTRAINT form_completions_form_type_check
      CHECK (form_type IN ('ta6', 'ta10', 'ta6_ta10'));
  END IF;
END $$;
