-- Brief 2 of 5 — Supabase Separation Series
-- Creates the NUVU-owned chain_chase_state table.
-- Progression tracking data moves here from chain_links (EATOC-owned).
-- DO NOT modify, drop, or alter chain_links in any way.

CREATE TABLE IF NOT EXISTS chain_chase_state (
    id                              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_link_id                   UUID        NOT NULL,
    property_address                TEXT,
    solicitor_status                TEXT        DEFAULT 'not_set',
    solicitor_email                 TEXT,
    chain_solicitor_first_email_at  TIMESTAMPTZ,
    solicitor_acting_confirmed_at   TIMESTAMPTZ,
    chain_solicitor_intro_sent_at   TIMESTAMPTZ,
    last_chain_inform_sent_at       TIMESTAMPTZ,
    last_chain_request_sent_at      TIMESTAMPTZ,
    last_chain_solicitor_reply_at   TIMESTAMPTZ,
    chain_solicitor_unresponsive_at TIMESTAMPTZ,
    chain_solicitor_reinstate_prompt_at TIMESTAMPTZ,
    solicitor_details_requested     BOOLEAN     DEFAULT FALSE,
    created_at                      TIMESTAMPTZ DEFAULT now(),
    updated_at                      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chain_chase_state_chain_link_id_key UNIQUE (chain_link_id)
);

CREATE INDEX IF NOT EXISTS idx_chain_chase_state_chain_link_id
    ON chain_chase_state (chain_link_id);

CREATE INDEX IF NOT EXISTS idx_chain_chase_state_property_address
    ON chain_chase_state (property_address);

-- ── Backfill ─────────────────────────────────────────────────────────────────
-- chain_links is currently empty in production (confirmed Brief 1 test).
-- This is a safe idempotent backfill for any future data or re-runs.
-- chain_links has no property_address column; backfill sets it NULL.
INSERT INTO chain_chase_state (
    chain_link_id,
    property_address,
    solicitor_status,
    solicitor_email,
    chain_solicitor_first_email_at,
    solicitor_acting_confirmed_at,
    chain_solicitor_intro_sent_at,
    last_chain_inform_sent_at,
    last_chain_request_sent_at,
    last_chain_solicitor_reply_at,
    chain_solicitor_unresponsive_at,
    chain_solicitor_reinstate_prompt_at,
    solicitor_details_requested
)
SELECT
    id,
    NULL,
    solicitor_status,
    solicitor_email,
    chain_solicitor_first_email_at,
    solicitor_acting_confirmed_at,
    chain_solicitor_intro_sent_at,
    last_chain_inform_sent_at,
    last_chain_request_sent_at,
    last_chain_solicitor_reply_at,
    chain_solicitor_unresponsive_at,
    chain_solicitor_reinstate_prompt_at,
    solicitor_details_requested
FROM chain_links
WHERE
    solicitor_status IS DISTINCT FROM 'not_set'
    OR solicitor_email IS NOT NULL
    OR chain_solicitor_first_email_at IS NOT NULL
    OR solicitor_acting_confirmed_at IS NOT NULL
    OR chain_solicitor_intro_sent_at IS NOT NULL
    OR last_chain_inform_sent_at IS NOT NULL
    OR last_chain_request_sent_at IS NOT NULL
    OR last_chain_solicitor_reply_at IS NOT NULL
    OR chain_solicitor_unresponsive_at IS NOT NULL
    OR chain_solicitor_reinstate_prompt_at IS NOT NULL
    OR solicitor_details_requested IS TRUE
ON CONFLICT (chain_link_id) DO NOTHING;
