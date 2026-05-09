-- Chase Engine Phase B — sales_progression milestones, solicitor emails,
-- chase_messages.chase_date, local_authority_search_times seed.
-- Run in Supabase SQL editor after Phase A chase tables / needs_attention_schema.
--
-- Note: local_authority_search_times may already exist (needs_attention_schema.sql)
-- with columns local_authority_name, avg_turnaround_days — we only seed default.

-- ── sales_progression: Phase B milestones + solicitor email targets ──
ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS search_fees_confirmed timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS searches_ordered timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS searches_received timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS draft_contract_issued timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS seller_forms_returned timestamptz;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS buyer_solicitor_email text;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS seller_solicitor_email text;

COMMENT ON COLUMN sales_progression.search_fees_confirmed IS
  'Phase B Stage 4: buyer confirmed search fees paid to solicitor.';

COMMENT ON COLUMN sales_progression.draft_contract_issued IS
  'Phase B Stage 5: seller solicitor confirmed draft contract issued.';

-- ── chase_messages: optional scheduled / reference instant (Stage 6 results cadence) ──
ALTER TABLE chase_messages
  ADD COLUMN IF NOT EXISTS chase_date timestamptz;

COMMENT ON COLUMN chase_messages.chase_date IS
  'Phase B Stage 6: optional reference date (e.g. expected search turnaround) for auditing.';

-- ── local_authority_search_times: seed default row (existing table shape) ──
INSERT INTO local_authority_search_times (local_authority_name, avg_turnaround_days)
VALUES ('default', 15)
ON CONFLICT (local_authority_name) DO NOTHING;
