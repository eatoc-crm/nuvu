# NUVU — Architecture & Philosophy

## What NUVU Is

NUVU (branded "NewView") is a UK residential sales progression platform. It exists to reduce the average 21-week UK transaction time by replacing reactive "updates" with proactive, structured progression.

**Core ethos:** Proactive professional guidance with dignity and decorum. We sell dreams and aspirations, not aggressive timelines. Success means keeping buyers and sellers excited about their move, not scared. We beat the 21-week average through organisation, not pressure.

**Target:** 70–75% autonomous operation. AI handles structured communication and monitoring. Humans handle relationships, judgement calls, and seller advice.

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
├── app.py                    # Flask init + blueprint registration
├── shared.py                 # Supabase client, Resend config, shared constants
├── routes/
│   ├── auth.py               # Authentication & session management
│   ├── dashboard.py          # Main dashboard + DASHBOARD_HTML
│   ├── property_api.py       # Property detail API
│   ├── crm.py                # CRM views, helpers, constants
│   ├── progression.py        # Milestone updates + welcome engine
│   └── intake.py             # Inbound CRM API
├── connectors/               # CRM connectors
├── templates/                # HTML templates
├── email_engine.py           # Email sending via Resend
├── email_parser.py           # Inbound email parsing
├── completion_engine.py      # Completion logic
├── ai_parser.py              # AI content parsing
├── database.py               # Database helpers
└── db_supabase.py            # Supabase config
```

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
