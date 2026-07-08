-- Phase 0.1 Pipeline Truth Reset schema support.
-- Non-destructive only: do not clear or repush data from this script.

ALTER TABLE sales_pipeline
  DROP CONSTRAINT IF EXISTS sales_pipeline_alto_ref_key;

ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS do_not_chase boolean NOT NULL DEFAULT false;

ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS agreed_fee numeric;

ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS buyer_solicitor_contact_name text;
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS buyer_solicitor_phone text;
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS buyer_solicitor_address text;
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS seller_solicitor_contact_name text;
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS seller_solicitor_phone text;
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS seller_solicitor_address text;
