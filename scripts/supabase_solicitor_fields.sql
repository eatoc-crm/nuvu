-- Solicitor enrichment columns for sales_pipeline
-- Source: EATOC /api/nuvu/companies/:id and /api/nuvu/contacts/:id lookups
-- buyer_solicitor_email and seller_solicitor_email already exist — skipped here.
-- All columns are nullable TEXT.

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

COMMENT ON COLUMN sales_pipeline.buyer_solicitor_contact_name IS
  'Individual contact person at buyer solicitor firm (from EATOC contacts endpoint).';

COMMENT ON COLUMN sales_pipeline.buyer_solicitor_phone IS
  'COALESCE(contact.phone, company.phone) for buyer solicitor — used for escalation.';

COMMENT ON COLUMN sales_pipeline.buyer_solicitor_address IS
  'Buyer solicitor firm address (from EATOC companies endpoint).';

COMMENT ON COLUMN sales_pipeline.seller_solicitor_contact_name IS
  'Individual contact person at seller solicitor firm (from EATOC contacts endpoint).';

COMMENT ON COLUMN sales_pipeline.seller_solicitor_phone IS
  'COALESCE(contact.phone, company.phone) for seller solicitor — used for escalation.';

COMMENT ON COLUMN sales_pipeline.seller_solicitor_address IS
  'Seller solicitor firm address (from EATOC companies endpoint).';
