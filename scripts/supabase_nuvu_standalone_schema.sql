-- NUVU Standalone Schema — Brief 4 of 5 (Supabase Separation Series)
-- Run this in the NEW NUVU Supabase project (not the old shared one).
-- Creates all 13 tables NUVU needs. Safe to re-run (IF NOT EXISTS throughout).
-- Table order respects FK dependencies.

-- ── 1. sales_progression ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sales_progression (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    property_address            TEXT        NOT NULL,
    staff_initials              TEXT,
    sewage_type                 TEXT,
    offer_accepted              TEXT,
    memo_sent                   TEXT,
    exchange_date               TEXT,
    completion_date             TEXT,
    fee                         NUMERIC,
    invoice_status              TEXT,
    notes                       TEXT,
    status                      TEXT        DEFAULT 'active',
    branch                      TEXT        DEFAULT 'penrith',
    year                        INTEGER,
    buyer_solicitor             TEXT,
    vendor_solicitor            TEXT,
    sale_price                  NUMERIC,
    buyer_name                  TEXT,
    buyer_phone                 TEXT,
    buyer_email                 TEXT,
    vendor_name                 TEXT,
    vendor_phone                TEXT,
    vendor_email                TEXT,
    mortgage_broker             TEXT,
    surveyor                    TEXT,
    nuvu_notes                  TEXT,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    buyer_solicitor_firm_id     UUID,
    buyer_solicitor_contact_id  UUID,
    buyer_solicitor_ref         TEXT,
    buyer_solicitor_notes       TEXT,
    seller_solicitor_firm_id    UUID,
    seller_solicitor_contact_id UUID,
    seller_solicitor_ref        TEXT,
    seller_solicitor_notes      TEXT,
    agreed_by                   TEXT,
    alto_ref                    TEXT,
    buyers_solicitor            TEXT,
    vendors_solicitor           TEXT,
    our_ref                     TEXT,
    negotiator                  TEXT,
    searches_ordered            TIMESTAMPTZ,
    mortgage_offered            DATE,
    enquiries_raised            DATE,
    enquiries_answered          DATE,
    welcome_sent                TIMESTAMPTZ,
    protocol_forms_sent         DATE,
    protocol_forms_returned     DATE,
    searches_paid               DATE,
    searches_received           TIMESTAMPTZ,
    survey_instructed           DATE,
    draft_contract_sent         DATE,
    completion_target           DATE,
    exchange_agreed             DATE,
    phase                       INTEGER     DEFAULT 1,
    intake_received_at          TIMESTAMPTZ,
    seller_forms_returned       TIMESTAMPTZ,
    welcome_emails_sent         TIMESTAMPTZ,
    search_fees_confirmed       TIMESTAMPTZ,
    draft_contract_issued       TIMESTAMPTZ,
    buyer_solicitor_email       TEXT,
    seller_solicitor_email      TEXT,
    exchange_target_date        DATE,
    report_on_title             TIMESTAMPTZ,
    protocol_forms_received     DATE,
    CONSTRAINT sales_progression_property_address_key UNIQUE (property_address)
);

CREATE INDEX IF NOT EXISTS idx_sales_progression_status
    ON sales_progression (status);
CREATE INDEX IF NOT EXISTS idx_sales_progression_created_at
    ON sales_progression (created_at DESC);

-- ── 2. sales_pipeline (local read copy — populated by adapter sync) ───────────
CREATE TABLE IF NOT EXISTS sales_pipeline (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    alto_ref            TEXT,
    our_ref             TEXT,
    property_address    TEXT    NOT NULL,
    postcode            TEXT,
    status              TEXT,
    date_agreed         DATE,
    current_price       NUMERIC,
    est_exchange        DATE,
    exchange_date       DATE,
    est_completion      DATE,
    fee                 NUMERIC,
    fee_pct             NUMERIC,
    fee_percentage      NUMERIC,
    buyers_solicitor    TEXT,
    vendors_solicitor   TEXT,
    negotiator          TEXT,
    agreed_by           TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    buyer_name          TEXT,
    buyer_phone         TEXT,
    buyer_email         TEXT,
    vendor_name         TEXT,
    vendor_phone        TEXT,
    vendor_email        TEXT,
    mortgage_broker     TEXT,
    surveyor            TEXT,
    chain_status        TEXT    DEFAULT 'stable',
    local_authority     TEXT,
    buyer_solicitor_email   TEXT,
    seller_solicitor_email  TEXT,
    pipeline_status     TEXT,
    buyer_solicitor     TEXT,
    vendor_solicitor    TEXT,
    agreed_fee          NUMERIC,
    is_test             BOOLEAN DEFAULT false,
    CONSTRAINT sales_pipeline_property_address_key UNIQUE (property_address),
    CONSTRAINT sales_pipeline_alto_ref_key UNIQUE (alto_ref)
);

CREATE INDEX IF NOT EXISTS idx_sales_pipeline_status
    ON sales_pipeline (status);

-- ── 3. chain_links (local read copy — populated by adapter sync) ──────────────
CREATE TABLE IF NOT EXISTS chain_links (
    id                                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id                         UUID,
    link_address                        TEXT,
    chain_position                      TEXT,
    buyer_name                          TEXT,
    buyer_phone                         TEXT,
    buyer_email                         TEXT,
    seller_name                         TEXT,
    seller_phone                        TEXT,
    seller_email                        TEXT,
    estate_agent                        TEXT,
    buyer_solicitor                     TEXT,
    seller_solicitor                    TEXT,
    status                              TEXT,
    notes                               TEXT,
    created_at                          TIMESTAMPTZ DEFAULT now(),
    estate_agent_email                  TEXT,
    estate_agent_phone                  TEXT,
    solicitor_details_requested         BOOLEAN     DEFAULT false,
    solicitor_details_received          BOOLEAN     DEFAULT false,
    nuvu_introduced                     BOOLEAN     DEFAULT false,
    price                               NUMERIC,
    solicitor_firm                      TEXT,
    solicitor_phone                     TEXT,
    solicitor_email                     TEXT,
    updated_at                          TIMESTAMPTZ DEFAULT now(),
    solicitor_status                    TEXT        DEFAULT 'not_set',
    chain_solicitor_first_email_at      TIMESTAMPTZ,
    solicitor_acting_confirmed_at       TIMESTAMPTZ,
    chain_solicitor_intro_sent_at       TIMESTAMPTZ,
    last_chain_inform_sent_at           TIMESTAMPTZ,
    last_chain_request_sent_at          TIMESTAMPTZ,
    last_chain_solicitor_reply_at       TIMESTAMPTZ,
    chain_solicitor_unresponsive_at     TIMESTAMPTZ,
    chain_solicitor_reinstate_prompt_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_chain_links_property_id
    ON chain_links (property_id);

-- ── 4. solicitors ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS solicitors (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_name   TEXT,
    contact     TEXT,
    job_title   TEXT,
    telephone   TEXT,
    email       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ── 5. local_authority_search_times ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS local_authority_search_times (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    local_authority_name    TEXT        NOT NULL,
    avg_turnaround_days     INTEGER     NOT NULL,
    last_updated            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              TEXT
);

COMMENT ON TABLE local_authority_search_times IS
    'Expected local authority search turnaround; used by Needs Attention trigger 6.';

-- Seed default row used by the chase engine
INSERT INTO local_authority_search_times (local_authority_name, avg_turnaround_days)
VALUES ('default', 15)
ON CONFLICT DO NOTHING;

-- ── 6. preferred_surveyors ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS preferred_surveyors (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    agency_id       TEXT    NOT NULL DEFAULT 'dbe',
    surveyor_name   TEXT    NOT NULL,
    surveyor_firm   TEXT,
    contact_email   TEXT,
    contact_phone   TEXT,
    coverage_area   TEXT,
    google_rating   NUMERIC,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_preferred_surveyors_agency
    ON preferred_surveyors (agency_id);

COMMENT ON TABLE preferred_surveyors IS
    'Agency-specific surveyor recommendations (Progression Engine spec §5.2).';

-- ── 7. inbound_emails ─────────────────────────────────────────────────────────
-- property_id references sales_progression(id) — FK kept soft so missing rows
-- don't block inserts from Channel 3 when progression row lags slightly.
CREATE TABLE IF NOT EXISTS inbound_emails (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             INTEGER     NOT NULL,
    sender_email        TEXT,
    sender_name         TEXT,
    subject             TEXT,
    body_preview        TEXT,
    received_at         TIMESTAMPTZ NOT NULL,
    property_id         UUID        REFERENCES sales_progression (id) ON DELETE SET NULL,
    matched_by          TEXT,
    match_confidence    TEXT        DEFAULT 'unmatched',
    is_duplicate        BOOLEAN     DEFAULT false,
    duplicate_of        UUID,
    duplicate_resolution TEXT,
    ai_category         TEXT,
    ai_summary          TEXT,
    human_confirmed     BOOLEAN     DEFAULT false,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inbound_emails_property_id
    ON inbound_emails (property_id);
CREATE INDEX IF NOT EXISTS idx_inbound_emails_received_at
    ON inbound_emails (received_at DESC);

-- ── 8. chase_messages ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chase_messages (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id             UUID        NOT NULL REFERENCES sales_progression (id) ON DELETE CASCADE,
    chase_stage             TEXT        NOT NULL,
    chase_day               INTEGER     NOT NULL DEFAULT 0,
    recipient_type          TEXT        NOT NULL,
    recipient_email         TEXT,
    message_type            TEXT        NOT NULL DEFAULT 'chase'
                                            CHECK (message_type IN ('chase', 'flag_to_team')),
    subject                 TEXT,
    body_preview            TEXT,
    sent_at                 TIMESTAMPTZ,
    response_received       BOOLEAN     NOT NULL DEFAULT false,
    response_received_at    TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    chase_date              TIMESTAMPTZ,
    chain_link_id           UUID
);

-- Duplicate guard: separate partial indexes mirror the live DB
CREATE UNIQUE INDEX IF NOT EXISTS idx_chase_messages_cadence_no_chain_link
    ON chase_messages (property_id, chase_stage, chase_day)
    WHERE chain_link_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_chase_messages_cadence_chain_link
    ON chase_messages (property_id, chase_stage, chase_day, chain_link_id)
    WHERE chain_link_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chase_messages_property
    ON chase_messages (property_id);
CREATE INDEX IF NOT EXISTS idx_chase_messages_sent
    ON chase_messages (sent_at) WHERE sent_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chase_messages_chain_link
    ON chase_messages (chain_link_id) WHERE chain_link_id IS NOT NULL;

COMMENT ON TABLE chase_messages IS
    'Phase A/B/C chase log; duplicate guard via partial unique indexes on (property_id, chase_stage, chase_day).';

-- ── 9. chase_confirmations ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chase_confirmations (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id         UUID        NOT NULL REFERENCES sales_progression (id) ON DELETE CASCADE,
    inbound_email_id    UUID        REFERENCES inbound_emails (id) ON DELETE SET NULL,
    suggested_milestone TEXT        NOT NULL,
    suggested_value     TIMESTAMPTZ,
    email_snippet       TEXT,
    status              TEXT        NOT NULL DEFAULT 'pending'
                                        CHECK (status IN ('pending', 'confirmed', 'dismissed')),
    confirmed_by        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actioned_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_chase_confirmations_pending
    ON chase_confirmations (status, created_at DESC)
    WHERE status = 'pending';

COMMENT ON TABLE chase_confirmations IS
    'Inbound email milestone suggestions; dashboard Confirm/Dismiss before updating sales_progression.';

-- ── 10. portal_sessions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portal_sessions (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    property_address    TEXT        NOT NULL,
    seller_name         TEXT        NOT NULL,
    seller_email        TEXT,
    form_type           TEXT        NOT NULL,
    token               TEXT        NOT NULL,
    token_expires_at    TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    property_id         UUID,
    status              TEXT        NOT NULL DEFAULT 'draft',
    submitted_at        TIMESTAMPTZ,
    link_sent_at        TIMESTAMPTZ,
    CONSTRAINT portal_sessions_token_key
        UNIQUE (token) WHERE (token IS NOT NULL AND length(trim(token)) > 0)
);

CREATE INDEX IF NOT EXISTS portal_sessions_created_at_idx
    ON portal_sessions (created_at DESC);

COMMENT ON TABLE portal_sessions IS
    'Seller TA6/TA10 portal sessions; address matches utils.address.normalise_address for dashboard linking.';

-- ── 11. form_responses ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS form_responses (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID        NOT NULL REFERENCES portal_sessions (id) ON DELETE CASCADE,
    section_key     TEXT        NOT NULL,
    question_key    TEXT        NOT NULL,
    answer          JSONB,
    status          TEXT        NOT NULL DEFAULT 'in_progress',
    ai_conversation JSONB,
    updated_at      TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT form_responses_session_question_key UNIQUE (session_id, question_key)
);

CREATE INDEX IF NOT EXISTS idx_form_responses_session_id
    ON form_responses (session_id);

-- ── 12. form_completions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS form_completions (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID    NOT NULL REFERENCES portal_sessions (id) ON DELETE CASCADE,
    property_address    TEXT    NOT NULL,
    form_type           TEXT    NOT NULL CHECK (form_type IN ('ta6', 'ta10')),
    status              TEXT    NOT NULL DEFAULT 'in_progress',
    questions_answered  INTEGER NOT NULL DEFAULT 0,
    questions_total     INTEGER NOT NULL DEFAULT 0,
    pdf_path            TEXT,
    reviewed_by         TEXT,
    reviewed_at         TIMESTAMPTZ,
    dispatched_at       TIMESTAMPTZ,
    dispatched_to       TEXT,
    CONSTRAINT form_completions_session_id_key UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS form_completions_property_address_idx
    ON form_completions (property_address);

-- ── 13. chain_chase_state ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chain_chase_state (
    id                                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_link_id                       UUID        NOT NULL,
    property_address                    TEXT,
    solicitor_status                    TEXT        DEFAULT 'not_set',
    solicitor_email                     TEXT,
    chain_solicitor_first_email_at      TIMESTAMPTZ,
    solicitor_acting_confirmed_at       TIMESTAMPTZ,
    chain_solicitor_intro_sent_at       TIMESTAMPTZ,
    last_chain_inform_sent_at           TIMESTAMPTZ,
    last_chain_request_sent_at          TIMESTAMPTZ,
    last_chain_solicitor_reply_at       TIMESTAMPTZ,
    chain_solicitor_unresponsive_at     TIMESTAMPTZ,
    chain_solicitor_reinstate_prompt_at TIMESTAMPTZ,
    solicitor_details_requested         BOOLEAN     DEFAULT false,
    created_at                          TIMESTAMPTZ DEFAULT now(),
    updated_at                          TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chain_chase_state_chain_link_id_key UNIQUE (chain_link_id)
);

CREATE INDEX IF NOT EXISTS idx_chain_chase_state_chain_link_id
    ON chain_chase_state (chain_link_id);
CREATE INDEX IF NOT EXISTS idx_chain_chase_state_property_address
    ON chain_chase_state (property_address);

-- ── Verification query — run after creation to confirm all 13 tables exist ───
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN (
--     'sales_progression','sales_pipeline','chain_links',
--     'solicitors','local_authority_search_times','preferred_surveyors',
--     'inbound_emails','chase_messages','chase_confirmations',
--     'portal_sessions','form_responses','form_completions','chain_chase_state'
--   )
-- ORDER BY table_name;
-- Expected: 13 rows
