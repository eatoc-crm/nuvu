# NUVU — Architecture & Philosophy

## What NUVU Is

NUVU (branded "NewView") is a UK residential sales progression platform. It exists to reduce the average 21-week UK transaction time by replacing reactive "updates" with proactive, structured progression.

**Core ethos:** Proactive professional guidance with dignity and decorum. We sell dreams and aspirations, not aggressive timelines. Success means keeping buyers and sellers excited about their move, not scared. We beat the 21-week average through organisation, not pressure.

**Target:** 70–75% autonomous operation. AI handles structured communication and monitoring. Humans handle relationships, judgement calls, and seller advice.

**Progression engine (authoritative):** Chase cadences, chain rules, Needs Attention triggers, and Supabase milestone mapping are defined in [`docs/progression-engine-spec.md`](docs/progression-engine-spec.md). When a brief or implementation disagrees with that file, the spec wins.

---

## CRM-Agnostic Design

NUVU is **not** a CRM. It receives data from CRMs via a standardised intake API.

- **EATOC** is the current beta CRM (David Britton's own estate agency CRM)
- Future CRMs: Alto, Street, Reapit, Dezrez, Loop
- NUVU never talks directly to any CRM's database — all data flows through `/api/intake`
- EATOC-specific logic belongs in EATOC, not in NUVU

---

## Two-Phase Progression Model

### Phase 1 — Paperwork Lockdown (Sequential, Non-Negotiable)

These steps must happen in order. Most deals stall here — between 2 and 6 weeks can be lost. This is where NUVU earns its value.

1. **Welcome/Introduction** — NUVU introduces itself to all parties within 1 hour of sales memorandum. Explains the journey, sets expectations, reconfirms target dates.
2. **Protocol forms** — Clients fill in and return protocol forms to their solicitors. This is step one of everything.
3. **Searches ordered and fees paid** — Foundation of the legal process. Suggest expediting if the timeline is tight.
4. **Searches received** — Confirm receipt, flag any delays.
5. **Survey instructed** — Buyer's survey booked and scheduled.

**AI tone in Phase 1:** Professional, timely, clear. Guide people forward — never bully or pressure. Every communication should make the buyer/seller feel supported and excited about their move.

### Phase 2 — Parallel Track (Flexible, Overlapping)

Once Phase 1 is complete, the deal has momentum. These milestones progress in parallel:

- Mortgage offer progress
- Solicitor draft contract review
- Enquiries raised
- Replies to enquiries received
- Final mortgage offer confirmed
- Exchange date proposed and agreed
- Completion date locked

**AI tone in Phase 2:** Lighter touch. Monitoring, occasional prompts, flag issues for human escalation.

---

## Inbound Data Channels

### Channel 1 — Dedicated NUVU Email

`davidbrittonestates@brandnuvu.co.uk` — the primary sales progression contact address. Solicitors, brokers, surveyors reply here. NUVU parses directly.

### Channel 2 — Legacy Email Parsing

`sales@brittonestates.co.uk` / `salesprog@brittonestates.co.uk` — safety net for contacts who don't use the NUVU address. NUVU monitors and parses for progression-relevant content.

### Channel 3 — EATOC Note Feed (Permanent Sync)

Any note added to a buyer or seller card in EATOC is pushed to NUVU in real time. **Hard rule: only properties that exist in NUVU (Under Offer and beyond).** No exceptions.

### Email Matching Rules (Priority Order)

1. **Sender email match** — sender matches a buyer, seller, broker, or surveyor email on a NUVU property → auto-linked
2. **Solicitor match** — known solicitor email → scan subject/body for property address or postcode → linked
3. **No match** — flagged for human review (never discarded)

### Deduplication

If the same email arrives via two channels, the duplicate is flagged as "for reference — duplication" with a dropdown for human review.

### AI Authority (Beta Mode)

AI parses and categorises all inbound but does **NOT** auto-update milestones. Everything is flagged for human confirmation. Kill switch (`WELCOME_ENGINE_ENABLED`) controls outbound. Separate kill switch for auto-milestone-updates to be added.

---

## Human Intervention Points

- Early detection of buyer underperformance → negotiator has conversation with seller
- Any Phase 1 milestone stall → human escalation
- All major decisions remain human-led
- "Cut them free" conversations are always human, never AI

---

## File Structure

```
nuvu-live/
├── docs/
│   └── progression-engine-spec.md  # SSOT: cadences, Needs Attention, milestones
├── app.py                    # Flask init + blueprint registration
├── shared.py                 # Supabase client, Resend config, shared constants
├── routes/
│   ├── auth.py               # Authentication & session management
│   ├── dashboard.py          # Main dashboard + DASHBOARD_HTML
│   ├── property_api.py       # Property detail API
│   ├── crm.py                # CRM views, helpers, constants
│   ├── progression.py        # Milestone updates + welcome engine
│   ├── chase_engine.py       # Phases A + B + C chase cadence, inbound classification, confirmations API
│   ├── chain_chase.py        # Track 6 — chain solicitor outreach, reinstatement, inform/request
│   └── intake.py             # Inbound CRM API
├── connectors/               # CRM connectors
├── templates/                # HTML templates
├── utils/
│   ├── chase_templates.py    # Chase copy (from progression-engine-spec.md)
│   └── chase_scheduler.py  # 15-minute cadence thread
├── scripts/
│   ├── supabase_chase_engine_tables.sql  # chase_messages, chase_confirmations, preferred_surveyors
│   ├── supabase_chase_phase_b_columns.sql  # Phase B progression columns + chase_messages.chase_date + LA seed
│   └── supabase_chain_chase_columns.sql  # chain_links Track 6 columns + chase_messages.chain_link_id
├── email_engine.py           # Email sending via Resend
├── email_parser.py           # Inbound email parsing
├── completion_engine.py      # Completion logic
├── ai_parser.py              # AI content parsing
├── database.py               # Database helpers
└── db_supabase.py            # Supabase config
```

---

## Chase Engine (Phases A, B, C)

- **Kill switch:** `CHASE_ENGINE_ENABLED` — default false. When false, the 15-minute cadence still runs and logs what it would send; outbound Resend sends are skipped. Inbound classification still creates `chase_confirmations` rows for staff review.
- **Schema:** Run `scripts/supabase_chase_engine_tables.sql` in Supabase. `chase_messages.property_id` and `chase_confirmations.property_id` reference **`sales_progression.id`** (same as `inbound_emails.property_id`).
- **Phase B schema:** Run `scripts/supabase_chase_phase_b_columns.sql` — adds `search_fees_confirmed`, `searches_ordered`, `searches_received`, `draft_contract_issued`, `seller_forms_returned` (if missing), `buyer_solicitor_email`, `seller_solicitor_email`, optional `chase_messages.chase_date`, and seeds `local_authority_search_times` default row (`default`, 15 days) when that table exists.
- **Phase B behaviour:** Stages 4–6 (buyer search-fee awareness; seller’s solicitor draft contract; buyer’s solicitor searches ordered / results). Day-0 sends fire on milestone confirm (`/api/chase/confirmations/.../confirm`) and when staff PATCHes the same columns via `/api/progression`. Cadence follow-ups run in the same 15-minute sweep as Phase A. Duplicate guard: `(property_id, chase_stage, chase_day)` on `chase_messages` with `chain_link_id` null for property-level chases.
- **Negotiator flags:** Day 4 “flag to team” emails use `CHASE_TEAM_EMAIL` when set; otherwise the first address in `NUVU_ALLOWED_EMAILS`.
- **Scheduler:** Set `CHASE_SCHEDULER_DISABLED=true` to prevent the background thread (e.g. local tests).

## Chase Engine (Phase C — Stages 7 & 8)

- **SSOT alignment:** `docs/progression-engine-spec.md` wins on naming. External Phase C briefs may say “enquiries sent”; in code and schema that milestone is **`enquiries_raised`** (already on `sales_progression`).
- **New columns:** Run `scripts/supabase_chase_phase_c_columns.sql` — adds `exchange_target_date` (DATE) and `report_on_title` (timestamptz). PATCH overlay list in `db_supabase.py` includes both.
- **Stage 7:** Fires only when **both** `searches_received` and `survey_instructed` are set. Sub-stage 7a chases the buyer’s solicitor until `enquiries_raised`; 7b chases the seller’s solicitor until `enquiries_answered`. Compound day-0: when staff confirms either `searches_received` or `survey_instructed` via `chase_confirmations`, the engine immediately sends 7a day 0 if the other milestone is already set (cadence also covers this).
- **Report on title:** After `enquiries_answered`, a short cadence to the buyer’s solicitor until `report_on_title`.
- **Stage 8 (exchange target):** Triggered when `enquiries_raised` is set; runs **in parallel** with 7b. NUVU **states** the target exchange date (does not ask solicitors for it). Target resolution: manual `exchange_target_date`, else `est_completion` / `completion_date` minus 14 calendar days if present on pipeline/progression, else `offer_accepted` + **50 Mon–Fri working days**. First resolved target is persisted when missing. Solicitor emails: `sales_pipeline.buyers_solicitor_email` / `vendors_solicitor_email` when present.
- **After target date:** If the target date is in the past and the property is not exchanged, Stage 8 sends stop; Needs Attention surfaces **“Exchange target date passed — negotiator to review.”** No writes to `sales_pipeline` for exchanged status.

## Chain chase (Track 6)

- **Kill switch:** `CHAIN_CHASE_ENABLED` — default false. When false, the 15-minute cadence still evaluates chain links and logs dry-run sends (no Resend). Independent of `CHASE_ENGINE_ENABLED` for Track 6 outbound.
- **Schema:** Run `scripts/supabase_chain_chase_columns.sql`. Adds per–chain-link timestamps and `solicitor_status` / `solicitor_email` on `chain_links`, plus nullable `chase_messages.chain_link_id` and partial unique indexes so multiple chain solicitors on one subject property do not collide on duplicate detection. Track 5’s boolean `solicitor_details_requested` (chain agent email) is unchanged; Track 6 cadence anchors use `chain_solicitor_intro_sent_at` / `chain_solicitor_first_email_at`.
- **Triggers:** Phase 1 when `solicitor_email` (or an email embedded in buyer/seller solicitor text) is present and intro not yet sent; nudges Day 3 / 6; Day 9 negotiator flag in `nuvu_notes` + `solicitor_status = unresponsive`; 48h later a reinstate reminder note; keywords `reinstate` / `no contact` in NUVU Notes or inbound Ch3 body; replies from the solicitor email set `confirmed` and start inform + Week 4/8 request cadence. Milestone PATCH / chase confirmation fires **inform** emails to confirmed chain solicitors.
- **Needs Attention:** `chain_solicitor_unresponsive` cards when any link on the subject property is unresponsive.

---

## Infrastructure

| Resource | Detail |
|---|---|
| Live URL | https://nuvu-production.up.railway.app/ |
| Custom domain | app.brandnuvu.co.uk (not yet configured) |
| GitHub | github.com/eatoc-crm/nuvu (branch: main) |
| Local dir | /Users/davidbritton/nuvu-live |
| Supabase | grosqsxnwhuvazgbjwan.supabase.co |
| Deploy | Git push to main → Railway autodeploy |
| Email sending | Resend (salesprog@brittonestates.co.uk) |

---

## Key Rules

1. **Nothing reaches the outside world without explicit sign-off.** All outbound features require a kill switch and explicit activation.
2. **Status is human-set, never automatic.** Exchanged status is a deliberate human interaction. Status comes from `sales_pipeline` only.
3. **Only Under Offer+ properties exist in NUVU.** The EATOC note feed, email parsing, and all processing only applies to properties in NUVU. No exceptions.
4. **100% data accuracy.** "Close enough" is never acceptable.
5. **CRM-agnostic from the start.** NUVU's intake API uses a mapping layer. It is not built around any specific CRM's data structure.
6. **Decisions locked before briefs are written.** Briefs to Cursor must be complete and unambiguous.
7. **Risks flagged before builds, not after.** Compliance, data, and operational risks surfaced at design time.
8. **Tone: professional dignity, not aggression.** Every AI communication should make people feel supported and excited. Consistent and persistent, never pushy or low-rent.

---

## Dashboard colour palette (live UI)

The main dashboard (`DASHBOARD_HTML` in `routes/dashboard.py`) uses these accent colours:

- **NUVU green** `#C5D93A` — active tab, on-track / positive indicators, milestone progress and chips for healthy states, leaderboard up-arrows and fast transaction pills (with dark olive text `#2A3A0C` / `#4A5A1A` for contrast).
- **Deep claret** `#962D3E` — needs-attention, stalled / at-risk, warnings, recommended leaderboard accent where used.
- **Navy** `#1B3A5C` — toolbar, headings, completed milestone chips, numeric emphasis.
- **Warm page** `#F5F3EF` — main content background below the hero; white cards sit on top.

Funnel chart row colours may still use intermediate blues/greens for legibility; they are decorative, not status semantics.

## Pipeline Forecast (dashboard)

The **Pipeline Forecast** block is **read-only**. It aggregates what is already in the live stack (EATOC plus Supabase overlays): it **must not** insert, update, or delete rows in `sales_pipeline` or `sales_progression`. Those tables are the source of truth for pipeline state; the forecast only reads merged in-memory property rows, applies the agreed milestone-score heuristic for forward allocation (not `completion_target`), and surfaces counts, values, and fees. Other routes (intake, progression patches, and so on) continue to own writes to those tables where product behaviour requires it.

## Tabbed dashboard and service leaderboards

The main dashboard HTML (`DASHBOARD_HTML` in `routes/dashboard.py`) uses a **tab bar** under the hero with seven views: **Properties** (default), **Pipeline**, **Portal**, **Solicitors**, **Mortgage**, **Surveyors**, and **Removals**. Which tab is active is driven by the URL **fragment** (`#properties`, `#pipeline`, `#portal`, and so on) so bookmarks and reloads preserve the view. All tab bodies stay in the DOM; inactive panels are hidden with CSS so switching tabs does not tear down the property list or the pipeline block.

The **Pipeline** tab contains only the Pipeline Forecast section (it is no longer duplicated above the property list). **Portal** does not yet embed a dedicated staff admin UI: buyer/vendor flows and TA6/TA10 tooling live under the `portal` and `portal_forms` blueprints (`/portal`, `/portal/form`, review routes, staff property preview). The Portal tab currently explains that and links to `/portal`; per-property portal actions remain in the property modal.

**Solicitors / Mortgage / Surveyors / Removals** render a shared leaderboard card layout fed by **`LEADERBOARD_TABS`** in `routes/dashboard.py`: hardcoded Lancashire-style demo rows only (no Supabase reads or writes for leaderboards). When real leaderboards ship, they are expected to load from a future **leaderboard/reviews** table or API — not from `sales_pipeline` or `sales_progression`.
