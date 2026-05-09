-- Track 6 — chain solicitor chase + milestone emails (NUVU brief Session 19).
-- Run in Supabase SQL editor after reviewing existing chain_links columns.
-- Track 5 uses boolean solicitor_details_requested; Track 6 uses separate timestamps below.

-- ── chain_links (Track 6) ─────────────────────────────────────────
ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS solicitor_status text DEFAULT 'not_set';

COMMENT ON COLUMN chain_links.solicitor_status IS
  'Track 6: not_set | contacted | unresponsive | confirmed';

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS solicitor_email text;

COMMENT ON COLUMN chain_links.solicitor_email IS
  'Direct email for chain-side solicitor (Track 6 outreach recipient).';

-- When the first Track 6 email was sent (cadence day 0 anchor).
ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS chain_solicitor_first_email_at timestamptz;

-- When the chain solicitor confirmed they are acting (reply / confirmed status).
ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS solicitor_acting_confirmed_at timestamptz;

-- When Phase 1 introduction was last sent (reinstate resets sequence visually).
ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS chain_solicitor_intro_sent_at timestamptz;

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS last_chain_inform_sent_at timestamptz;

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS last_chain_request_sent_at timestamptz;

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS last_chain_solicitor_reply_at timestamptz;

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS chain_solicitor_unresponsive_at timestamptz;

ALTER TABLE chain_links
  ADD COLUMN IF NOT EXISTS chain_solicitor_reinstate_prompt_at timestamptz;

-- ── chase_messages.chain_link_id (nullable FK) ────────────────────
ALTER TABLE chase_messages
  ADD COLUMN IF NOT EXISTS chain_link_id uuid REFERENCES chain_links (id) ON DELETE SET NULL;

-- Replace single-property cadence unique with partial indexes so chain rows can share
-- (property_id, chase_stage, chase_day) across different chain_link_id values.
ALTER TABLE chase_messages DROP CONSTRAINT IF EXISTS chase_messages_one_send_per_cadence;

CREATE UNIQUE INDEX IF NOT EXISTS idx_chase_messages_cadence_no_chain_link
  ON chase_messages (property_id, chase_stage, chase_day)
  WHERE chain_link_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_chase_messages_cadence_chain_link
  ON chase_messages (property_id, chase_stage, chase_day, chain_link_id)
  WHERE chain_link_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chase_messages_chain_link
  ON chase_messages (chain_link_id)
  WHERE chain_link_id IS NOT NULL;
