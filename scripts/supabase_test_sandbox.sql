-- NUVU test sandbox — 8 fake properties for Chase Engine / dashboard testing.
-- Safe to re-run: removes prior Testington sandbox rows, then re-inserts.
-- Run in Supabase SQL editor (service role / DDL-capable session).

-- ── 1. Columns on sales_pipeline ─────────────────────────────
ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS is_test boolean NOT NULL DEFAULT false;

ALTER TABLE sales_pipeline
  ADD COLUMN IF NOT EXISTS buyer_type text;

COMMENT ON COLUMN sales_pipeline.is_test IS
  'When true, row is sandbox test data; hidden from dashboard aggregates by default.';

-- ── 2. Remove any previous sandbox at these addresses ─────────
DELETE FROM chase_messages
WHERE property_id IN (
    SELECT sp.id
    FROM sales_progression sp
    WHERE sp.property_address LIKE '%, Testington, TS1 1A%'
  );

DELETE FROM chase_confirmations
WHERE property_id IN (
    SELECT sp.id
    FROM sales_progression sp
    WHERE sp.property_address LIKE '%, Testington, TS1 1A%'
  );

DELETE FROM portal_sessions
WHERE property_id IN (
    SELECT p.id
    FROM sales_pipeline p
    WHERE p.property_address LIKE '%, Testington, TS1 1A%'
  );

DELETE FROM sales_progression
WHERE property_address LIKE '%, Testington, TS1 1A%';

DELETE FROM sales_pipeline
WHERE property_address LIKE '%, Testington, TS1 1A%';

-- ── 3. Constants (emails deliver to David via plus-addressing) ─
-- Buyer / seller / solicitors / negotiator per test brief.

-- ── 4. sales_progression (8 rows) then sales_pipeline (8 rows) ─
-- Timestamps use UTC now() for relative chase testing.

INSERT INTO sales_progression (
  property_address,
  status,
  buyer_name,
  buyer_email,
  buyer_phone,
  vendor_name,
  vendor_email,
  vendor_phone,
  offer_accepted,
  memo_sent,
  welcome_emails_sent,
  protocol_forms_returned,
  seller_forms_returned,
  survey_instructed,
  searches_ordered,
  searches_received,
  draft_contract_sent,
  created_at
)
VALUES
  -- 1 Fresh — no milestones
  (
    '11 Sandbox Lane, Testington, TS1 1AA',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 14)::timestamptz,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '12 days')
  ),
  -- 2 Welcome = now (Day 1 chases)
  (
    '22 Sandbox Lane, Testington, TS1 1AB',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 10)::timestamptz,
    NULL,
    CURRENT_TIMESTAMP,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '8 days')
  ),
  -- 3 Welcome 3 days ago
  (
    '33 Sandbox Lane, Testington, TS1 1AC',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 20)::timestamptz,
    NULL,
    (CURRENT_TIMESTAMP - interval '3 days'),
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '40 days')
  ),
  -- 4 Welcome 5 days ago (Day 4 flag / needs attention)
  (
    '44 Sandbox Lane, Testington, TS1 1AD',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 45)::timestamptz,
    NULL,
    (CURRENT_TIMESTAMP - interval '5 days'),
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '95 days')
  ),
  -- 5 Protocol forms returned now (Stage 4/5); welcome older
  (
    '55 Sandbox Lane, Testington, TS1 1AE',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 12)::timestamptz,
    (CURRENT_TIMESTAMP - interval '10 days'),
    (CURRENT_TIMESTAMP - interval '10 days'),
    CURRENT_TIMESTAMP,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '18 days')
  ),
  -- 6 Survey instructed 2 days ago (post-survey path after day 3)
  (
    '66 Sandbox Lane, Testington, TS1 1AF',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 15)::timestamptz,
    (CURRENT_TIMESTAMP - interval '8 days'),
    (CURRENT_TIMESTAMP - interval '8 days'),
    (CURRENT_TIMESTAMP - interval '6 days'),
    (CURRENT_TIMESTAMP - interval '6 days'),
    (CURRENT_TIMESTAMP - interval '2 days'),
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '35 days')
  ),
  -- 7 Phase 1 complete / high milestone score
  (
    '77 Sandbox Lane, Testington, TS1 1AG',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 30)::timestamptz,
    (CURRENT_TIMESTAMP - interval '25 days'),
    (CURRENT_TIMESTAMP - interval '25 days'),
    (CURRENT_TIMESTAMP - interval '20 days'),
    (CURRENT_TIMESTAMP - interval '18 days'),
    (CURRENT_TIMESTAMP - interval '15 days'),
    (CURRENT_TIMESTAMP - interval '12 days'),
    (CURRENT_TIMESTAMP - interval '10 days'),
    (CURRENT_TIMESTAMP - interval '8 days'),
    (CURRENT_TIMESTAMP - interval '50 days')
  ),
  -- 8 Mortgage buyer, no survey — welcome set so survey chases use mortgage branch
  (
    '88 Sandbox Lane, Testington, TS1 1AH',
    'Under Offer',
    'Test Buyer',
    'david+testbuyer@brittonestates.co.uk',
    '07700900001',
    'Test Seller',
    'david+testseller@brittonestates.co.uk',
    '07700900002',
    (CURRENT_DATE - 7)::timestamptz,
    NULL,
    (CURRENT_TIMESTAMP - interval '2 days'),
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    (CURRENT_TIMESTAMP - interval '9 days')
  );

INSERT INTO sales_pipeline (
  property_address,
  postcode,
  status,
  agreed_fee,
  fee,
  negotiator,
  buyers_solicitor,
  vendors_solicitor,
  is_test,
  buyer_type,
  created_at
)
VALUES
  (
    '11 Sandbox Lane, Testington, TS1 1AA',
    'TS1 1AA',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '12 days')
  ),
  (
    '22 Sandbox Lane, Testington, TS1 1AB',
    'TS1 1AB',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '8 days')
  ),
  (
    '33 Sandbox Lane, Testington, TS1 1AC',
    'TS1 1AC',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '40 days')
  ),
  (
    '44 Sandbox Lane, Testington, TS1 1AD',
    'TS1 1AD',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '95 days')
  ),
  (
    '55 Sandbox Lane, Testington, TS1 1AE',
    'TS1 1AE',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '18 days')
  ),
  (
    '66 Sandbox Lane, Testington, TS1 1AF',
    'TS1 1AF',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '35 days')
  ),
  (
    '77 Sandbox Lane, Testington, TS1 1AG',
    'TS1 1AG',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'cash',
    (CURRENT_TIMESTAMP - interval '50 days')
  ),
  (
    '88 Sandbox Lane, Testington, TS1 1AH',
    'TS1 1AH',
    'SSTC',
    4000,
    4000,
    'David Britton',
    'Test Solicitor (Buyer) <david+testbsol@brittonestates.co.uk>',
    'Test Solicitor (Seller) <david+testssol@brittonestates.co.uk>',
    true,
    'mortgage',
    (CURRENT_TIMESTAMP - interval '9 days')
  );
