# NUVU Progression Engine

**Complete chase sequence, cadence & chain specification**

| | |
| --- | --- |
| Version | 1.0 |
| Date | 8 May 2026 |
| Owner | David Britton |

This is the **single source of truth** for all NUVU progression logic. Every Cursor brief, every dashboard feature, and every communication template must comply with this document. **If it contradicts a handover brief, this document wins.**

---

## 1. Philosophy

NUVU is proactive professional guidance delivered with dignity. Not aggressive, not pushy. Selling the dream of a smooth move. Consistent and persistent — but always warm. The tone is an experienced estate agent who knows exactly what needs to happen and when, gently steering every party toward completion.

- **Target:** Sub-90-day completions vs. UK national average of ~21 weeks (147 days).
- **Mechanism:** Organisation, not pressure. Make sure every party knows what’s needed, when, and why — then follow up until it’s done.
- **Communication rule:** Each party gets **one** message per milestone asking for **one** specific action. No overlap. No duplication. No robotic cadence.
- **Transparency:** All milestone status visible to buyers and sellers in their portal. Solicitor response delays are published. Accountability is the product.

---

## 2. The full progression sequence

Everything is **event-driven**. Each step triggers the next. **Calendar days** are chase cadences, not fixed schedules.

### Stage 0: Sales memorandum received

EATOC pushes memo to NUVU. Transaction begins. Chain details included where known.

- **Trigger:** Memo arrives via `/api/intake` or `/api/update`
- **Immediate action:** Welcome Engine fires (Track 1–5) within 1 hour.

### Stage 1: Welcome Engine (hour 0–1)

Five simultaneous emails to all parties confirming NUVU is managing the transaction:

| Track | Recipient | Purpose |
| --- | --- | --- |
| 1 | Buyer | Congratulations, next steps, survey/mortgage reminders |
| 2 | Seller | Sale confirmed, solicitor coordination, weekly chase promise |
| 3 | Buyer’s solicitor | Memorandum confirmation, search request, escalation channel |
| 4 | Seller’s solicitor | Memorandum confirmation, contract pack request |
| 5 | Chain estate agent(s) | Introduction; request names/addresses/solicitor details for their link |

**Track 5 note:** Chain agents will **not** share client contact details. Ask only for: client names, property address, solicitor name and firm. Mark `solicitor_details_requested = true` on `chain_links`.

### Stage 2: Protocol forms (day 1+)

The primary bottleneck in UK transactions. Industry average: 14–21 days. NUVU target: **7 days or fewer**.

#### 2a. Buyer protocol forms

| Day | Action | Message |
| --- | --- | --- |
| 1 | First nudge | Congratulations again — have you received your solicitor’s instruction letter and protocol forms? |
| 2 | Chase | Just checking in — have those forms arrived yet? |
| 3 | Chase | We know forms can feel overwhelming — let us know if you need any help. |
| 4 | Flag to team | No response after 3 days. Negotiator to follow up personally. |

**Rationale:** Buyer is in the honeymoon phase. Enthusiasm fades fast. Push early.

#### 2b. Seller TA6 & TA10

| Day | Action | Message |
| --- | --- | --- |
| 1 | First nudge | Have you sent back your Property Information Form and Fittings & Contents Form to your solicitor? If not, log into the portal and we’ll help you complete them. |
| 2 | Chase | These forms are the single biggest thing holding up your sale right now. |
| 3 | Chase | Most sellers find these forms confusing — our portal walks you through every question step by step. |
| 4 | Flag to team | No response. Negotiator to call seller directly. |

**Layman’s language only:** Never “TA6” or “TA10” in **seller-facing** copy. Use “Property Information Form” and “Fittings and Contents Form”.

**Portal link:** If the seller hasn’t completed forms, direct them to the TA6/TA10 portal for guided completion.

### Stage 3: Survey instruction (day 1+ — **parallel**)

Runs in parallel from day 1. **Does not** depend on solicitors being instructed or protocol forms being returned.

| Day | Buyer type | Message |
| --- | --- | --- |
| 1 | Cash buyer | Have you booked your survey yet? Surveyors are in high demand so best to get this booked as soon as possible. |
| 1 | Mortgage buyer | Has your mortgage broker booked your survey yet? Surveyors are in high demand so essential to get this booked as soon as possible. |
| 2 | Both | Chase: any progress on the survey booking? |
| 3 | Both | Chase. If no surveyor: recommend from agency panel or Google-reviewed local firms. |
| 4 | Both | Flag to team if still no booking. |

If the buyer has no surveyor: recommend one. **Beta:** DBE’s preferred panel. **External agencies:** their own panel or local Google-reviewed firms.

**Post-survey chase:** 3 days after survey date — “Has the survey taken place? Any issues?”

### Stage 4: Search fee payment

**Triggered:** Buyer protocol forms returned.

| Day | Action | Message |
| --- | --- | --- |
| 0 | Immediate | Did your solicitor request search fees when you sent your forms back? |
| 1 | Chase | If not requested: “Worth checking with your solicitor — searches can’t be ordered until fees are paid.” |
| 3 | Flag to team | No confirmation of fees paid. Negotiator to follow up. |

**Tone:** Checking, not chasing. Frame as “did your solicitor ask for this?” not “pay your fees.”

### Stage 5: Draft contract

**Triggered:** Seller TA6/TA10 returned.

| Day | Recipient | Message |
| --- | --- | --- |
| 0 | Seller’s solicitor | Protocol forms received — are you in a position to issue draft contract? |
| 1 | Seller’s solicitor | Chase: any update on the draft contract? |
| 2 | Seller’s solicitor | Chase. |
| 3 | Seller’s solicitor | Chase. |
| 4 | Flag to team | No draft contract after 4 days. Negotiator to escalate. |

If draft contract is delayed: ask seller’s solicitor to produce a plan so buyer’s solicitor can expedite searches independently.

### Stage 6: Searches ordered

**Triggered:** Search fees paid.

| When | Recipient | Message |
| --- | --- | --- |
| Day 0 | Buyer’s solicitor | Have searches been ordered? |
| Day 1 | Buyer’s solicitor | 24hr chase if no confirmation. |
| Confirmed | NUVU system | Look up local authority published turnaround time. Set chase date accordingly. |
| Chase date | Buyer’s solicitor | Searches were ordered [X] weeks ago. Published turnaround was [Y] weeks. Any update? |
| Chase +1d | Daily chase | Daily chase until searches received. Delay published in buyer/seller portal. |

**Local authority:** NUVU tells the solicitor the expected turnaround, not asks: “Searches ordered with [council]. Current published turnaround is [X] weeks. We’ll check back on [date].”

**Requires:** A local authority search turnaround lookup table. Updatable by DBE team. Future: auto-scraped.

### Stage 7: Enquiries

**Triggered:** Searches received **and** survey done.

| When | Recipient | Message |
| --- | --- | --- |
| Day 0 | Buyer’s solicitor | Searches are back and survey is completed — do you have everything you need to start raising enquiries? |
| Day 1 | Buyer’s solicitor | 24hr chase if no response. Delay published in portal. |
| Enquiries sent | Seller’s solicitor | Quick confirmation: “Did you receive the enquiries from [buyer’s solicitor]?” |
| +48hrs | Seller’s solicitor | 48hr chase for enquiry responses. Pleasant but firm. |
| Ongoing | Seller’s solicitor | Continue 48hr chase until all enquiries resolved. |

**Non-response from any solicitor:** 24hr chase. Published in client portal. *“I have no time for people being rude and not responding.”*

### Stage 8: Exchange date discussion

**Triggered:** Enquiries sent.

NUVU does **not** wait for enquiries to be resolved before starting the exchange conversation. The moment enquiries are sent over, NUVU starts working the chain on dates.

**Principle:** NUVU works with buyers, sellers, and chain to **agree** dates. Then **tells** the solicitors. Not the other way around.

| When | Recipient | Message |
| --- | --- | --- |
| Enquiries sent | Buyer + seller + chain | “As long as there are no major issues in the enquiries, shall we get some dates put through the chain?” |
| Same time | Buyer + seller | “Have you thought about dates for booking removals? There can sometimes be a delay so worth getting something pencilled in.” |
| Dates agreed | Both solicitors | “The chain has agreed [date]. Please work towards exchange on or before this date.” |
| +24hrs | Both solicitors | Daily chase if solicitors go quiet on hitting the agreed date. |

---

## 3. Chain handling

Every party in the chain follows the same milestone sequence, but triggered at different calendar dates based on when their memo went out and when information becomes available.

### 3.1 Chain discovery

- Chain details arrive from EATOC with the sales memo. Buyer/seller names and estate agent details for each link are included.
- Solicitor details for chain links may or may not be included.
- If solicitor details are missing: Track 5 auto-email fires to the chain estate agent requesting: client names, property address, solicitor name and firm.
- Chain agents will **not** share client contact details. Only names, addresses, solicitor details.

### 3.2 Chain outreach tracking

`chain_links` table tracks three booleans per link:

| Field | Meaning |
| --- | --- |
| `solicitor_details_requested` | Track 5 email sent to chain agent requesting details |
| `solicitor_details_received` | Chain agent has responded with solicitor name/firm |
| `nuvu_introduced` | NUVU has sent introduction email to chain solicitors |

### 3.3 Chain milestone tracking

- Once NUVU has chain solicitor details, it introduces itself to all chain solicitors with the same professional tone as Tracks 3/4.
- Milestones for each chain link are ticked as information comes in via email from chain agents — not from direct solicitor contact (those are other agents’ solicitors).
- Each chain link follows the same milestone sequence as the primary transaction.
- Chain parties may enter at different stages — a buyer further up the chain might be 6 weeks ahead. NUVU discovers their current position and tracks from there.

### 3.4 Chain communication rule

NUVU presents itself as a **sales progression system**, not an AI system, to external parties. Communication is structured so it doesn’t overlap and doesn’t sound automated. Each party in the chain gets milestone-specific messages at the appropriate time for their position.

---

## 4. Needs Attention dashboard

The dashboard front page is restructured into four sections, top to bottom:

1. **Needs Attention** (top) — only flagged properties  
2. **One month remaining**  
3. **Two to three months remaining**  
4. **Three months and over**  

**Time bucketing:** By `created_at` on `sales_pipeline`. 90+ days = “Three months and over”.

### 4.1 Needs Attention triggers

Every trigger is milestone-specific with defined cadences from this document. A property enters Needs Attention when any chase reaches its “flag to team” threshold (or equivalent detection below).

| Trigger | Flag day | Detection |
| --- | --- | --- |
| Buyer protocol forms overdue | Day 4 | `welcome_emails_sent` populated, `protocol_forms_returned` null **for buyer** |
| Seller TA6/TA10 overdue | Day 4 | `welcome_emails_sent` populated, `protocol_forms_returned` null **for seller** |
| Survey not booked | Day 4 | `welcome_emails_sent` populated, `survey_instructed` null |
| Search fees not paid | Day 3 | `protocol_forms_returned` populated (buyer), `searches_ordered` null |
| Draft contract overdue | Day 4 | `protocol_forms_returned` populated (seller), `draft_contract_sent` null |
| Searches overdue | Past published turnaround | `searches_ordered` populated, `searches_received` null, past local authority timeframe |
| Enquiries not raised | Day 1 | `searches_received` + survey done, `enquiries_raised` null, no response to prompt |
| Solicitor non-response | 24hrs | Any message to a solicitor with no response within 24 hours |
| Chain issue | Manual | Manual flag by team. Future: AI classification of inbound notes. |
| Survey issue | Manual | Manual flag. Survey concerns, renegotiation, valuation shortfall. |
| Chain breakdown | Manual | Manual flag. `chain_status` field: stable / at_risk / broken. |

### 4.2 Needs Attention card content

Each card shows:

- Property address and price  
- Which trigger(s) fired  
- How many days overdue  
- Suggested action for the negotiator  
- Quick-action button (e.g. “Call seller”, “Email solicitor”)  

---

## 5. Supporting data tables required

### 5.1 Local authority search turnaround

**Table:** `local_authority_search_times`

| Column | Notes |
| --- | --- |
| `local_authority_name` | Text, unique |
| `avg_turnaround_days` | Integer |
| `last_updated` | `timestamptz` |
| `updated_by` | Text |

Manually maintained by DBE team for beta. Future: auto-scraped from council websites.

### 5.2 Preferred surveyors

**Table:** `preferred_surveyors`

| Column | Notes |
| --- | --- |
| `id` | UUID, PK |
| `agency_id` | Text — multi-agency; `'dbe'` for beta |
| `surveyor_name` | Text |
| `surveyor_firm` | Text |
| `contact_email` | Text |
| `contact_phone` | Text |
| `coverage_area` | Text — geographic area covered |
| `google_rating` | Numeric |

When a buyer has no surveyor, NUVU recommends from this list.

---

## 6. Supabase milestone field mapping

How each stage maps to existing `sales_progression` columns:

| Stage | Column | Phase |
| --- | --- | --- |
| Welcome emails sent | `welcome_emails_sent` | Phase 1 |
| Protocol forms sent | `protocol_forms_sent` | Phase 1 |
| Protocol forms returned | `protocol_forms_returned` | Phase 1 |
| Searches ordered | `searches_ordered` | Phase 1 |
| Searches received | `searches_received` | Phase 1 |
| Survey instructed | `survey_instructed` | Phase 1 (parallel) |
| Mortgage offered | `mortgage_offered` | Phase 2 |
| Draft contract sent | `draft_contract_sent` | Phase 2 |
| Enquiries raised | `enquiries_raised` | Phase 2 |
| Enquiries resolved | `enquiries_resolved` | Phase 2 |
| Exchange | `exchange_date` | Phase 2 |

---

## 7. Beta-mode rules

- All AI-driven milestone updates require **human confirmation** before actioning.
- No outbound email fires without kill switch being **explicitly** enabled.
- Kill switches: `WELCOME_ENGINE_ENABLED`, `PORTAL_ENABLED`, `PORTAL_AI_ENABLED`, `PORTAL_DISPATCH_ENABLED`. (Chase engine: see product briefs for `CHASE_ENGINE_ENABLED` or equivalent.)
- Status (Exchanged) is always a **deliberate human action**, never automated.
- All communication templates require **David’s sign-off** before going live.
- Dry-run is the default for any Supabase write tool. `--write` must be explicit.

---

## Supersedes

This document supersedes all previous handover notes on progression logic, chase cadences, and Needs Attention triggers. **If in doubt, this document is correct.**

— End of specification —
