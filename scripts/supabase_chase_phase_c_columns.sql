-- Chase Engine Phase C — sales_progression columns (Stages 7 & 8).
-- Run in Supabase SQL editor. Idempotent (IF NOT EXISTS).
--
-- Note: Phase C brief names "enquiries_sent"; NUVU SSOT (docs/progression-engine-spec.md)
-- uses enquiries_raised for the same milestone — no duplicate column.

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS exchange_target_date date;

ALTER TABLE sales_progression
  ADD COLUMN IF NOT EXISTS report_on_title timestamptz;

COMMENT ON COLUMN sales_progression.exchange_target_date IS
  'NUVU-stated target exchange date (DATE). May be set by negotiator or defaulted by chase engine.';

COMMENT ON COLUMN sales_progression.report_on_title IS
  'Buyer''s solicitor confirmed report on title sent to buyer.';
