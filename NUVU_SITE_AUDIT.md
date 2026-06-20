# NUVU — Full Site Audit (read-only)

**Generated:** 2026-05-09  
**Scope:** All HTTP routes registered from `app.py` blueprints, `templates/`, environment kill switches, and outbound integrations.  
**Note:** The brief asked for `/home/claude/NUVU_SITE_AUDIT.md`; on this workspace the file is saved as **`NUVU_SITE_AUDIT.md`** at the repository root.

**Auth model:** `routes/auth.py` runs `require_login` on every request before blueprints. Exemptions are `AUTH_EXEMPT_PREFIXES` plus explicit portal branches in the same function. “Public” below means **no NUVU staff session** (`nuvu_email`); some public routes still require **API key** (`X-NUVU-API-KEY` / `X-API-Key`) or **portal session / token**.

---

## Site map (browser URLs)

Grouped for humans; **public without staff login** flagged.

### Staff / main app (session: `nuvu_email` required unless noted)

| URL | Description |
|-----|-------------|
| `/` | Main sales progression dashboard (inline `DASHBOARD_HTML`). |
| `/?show_test=…` | Same with optional Supabase sandbox test rows. |
| **Public:** `/login` | Magic-link login form (GET/POST). |
| **Public:** `/auth/verify?token=…` | Consumes magic link, sets session, redirects `/`. |
| **Public:** `/logout` | Clears session; redirects `/login`. |

### CRM live view (**public** — entire `/crm` tree exempt from staff login)

| URL | Description |
|-----|-------------|
| **Public:** `/crm` | Live EATOC-backed pipeline using same dashboard shell as `/` (different card click target). |
| **Public:** `/crm?show_test=…` | CRM view including sandbox test properties when enabled. |
| **Public:** `/crm/property/<prop_id>` | Single-property CRM detail (`crm_property_detail.html`). |

### Buyer/vendor portal (demo — separate `portal_demo` session)

| URL | Description |
|-----|-------------|
| **Public:** `/portal`, `/portal/` | Demo portal login or redirect to home. |
| **Public:** `/portal/login` | POST only — sets demo portal session. |
| **Public:** `/portal/home` | Portal “property overview” (inline HTML string). |
| **Public:** `/portal/logout` | Clears portal demo session. |

### Staff-only portal (requires **both** `nuvu_email` and staff checks in `portal.py`)

| URL | Description |
|-----|-------------|
| `/portal/staff/property-home?progression_id=…&role=buyer\|seller` | Staff preview of buyer/seller portal home. |
| `/portal/review/<session_id>` | Staff TA6/TA10 answer review before dispatch (`portal_review.html`). |

### Seller TA6/TA10 forms (**public** paths; session id or token is the secret)

| URL | Description |
|-----|-------------|
| **Public:** `/portal/form?session_id=…&form=…` | Conversational TA6/TA10 wizard (`portal_form.html`). |
| **Public:** `/portal/form/review?…` | Seller review / submit step (`portal_seller_review.html`). |
| **Public:** `/portal/form/ta6_ta10?token=…` | Magic-link entry → redirect into wizard. |
| **Public:** `/portal/form/submitted?session_id=…` | Post-submit thank-you (`portal_submitted.html`). |

### Not a “page” but browser-reachable patterns

- Static files under **`/static/`** (**public**).

---

## HTTP routes (every registered route)

Blueprint **URL prefixes:** `portal_bp` and `portal_forms_bp` use `url_prefix="/portal"`. All others use default `/`. `app.py` defines no routes of its own.

Legend: **Auth** = NUVU staff session unless exempt. **Response** = primary return type.

---

### `routes/auth.py` — `auth_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/login` | Shows magic-link login form. | Exempt (public). | `render_template_string(LOGIN_HTML)` | Yes — `auth_verify` redirect; dashboard guard redirect; forms link “log in” implicitly via `/`. |
| POST | `/login` | Validates email vs allowlist, rate-limits, emails magic link via Resend. | Exempt. | `LOGIN_HTML` + status 429 on rate limit | Yes — form `action="/login"`. |
| GET | `/auth/verify` | Validates token, sets `nuvu_email` session, redirects `/`. | Exempt. | Redirect or `LOGIN_HTML` error | Yes — link in magic email. |
| GET | `/logout` | Clears session. | Exempt. | Redirect `/login` | Yes — linked from dashboard template string. |

---

### `routes/dashboard.py` — `dashboard_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/` | Builds live dashboard data (EATOC + Supabase overlay + chase cards) and renders main UI. | **Staff session** (not exempt). | `render_template_string(DASHBOARD_HTML, …)` | Yes — primary app entry after login. |

---

### `routes/crm.py` — `crm_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/crm` | Same dashboard shell as `/` but data from EATOC API + CRM card JS linking to detail URLs. | **Exempt** — public (no staff login). | `render_template_string(DASHBOARD_HTML + CRM_OVERRIDE_JS, …)` | Yes — direct navigation; Needs Attention links from `utils/needs_attention.py` use `/crm/property/…`. |
| GET | `/crm/property/<prop_id>` | Single property CRM detail with timeline, chases, inbound, chain. | **Exempt** — public. | `render_template("crm_property_detail.html", …)` or error HTML | Yes — CRM_OVERRIDE_JS card clicks; back link in template to `/crm`. |
| POST | `/api/crm/notes/<prop_id>` | PATCHes `nuvu_notes` to EATOC property API for given id. | **Exempt** prefix `/api/crm/` — **no Flask session check**; handler does **not** verify `X-NUVU-API-KEY`. | `jsonify` | Yes — `crm_property_detail.html` `fetch` on save. |

---

### `routes/intake.py` — `intake_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| POST | `/api/intake` | Upserts `sales_pipeline` / `sales_progression` on Under Offer (or reversal); may trigger welcome engine. | **Exempt** + `require_nuvu_api_key()` in handler. | `jsonify` | Yes — EATOC / CRM integration (external callers). |
| POST | `/api/update` | Inserts EATOC note feed rows into `inbound_emails` and triggers inbound processing. | **Exempt** + API key in handler. | `jsonify` | Yes — EATOC note feed. |
| GET | `/api/duplicates` | Lists duplicate-flagged inbound emails pending resolution. | **Staff session required** (path **not** in `AUTH_EXEMPT_PREFIXES`) **and** API key in handler. | `jsonify` | **No in-repo references** — intended for tooling; browser-only clients would hit login redirect first. |
| POST | `/api/duplicates/<email_id>/resolve` | Records resolution for a duplicate inbound row. | Same as duplicates list. | `jsonify` | **No in-repo references.** |

---

### `routes/progression.py` — `progression_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| PATCH | `/api/progression/<prog_id>` | Updates allowed milestone fields on `sales_progression`; hooks chain chase + chase engine. | **Staff session** (not exempt). | `jsonify` | Yes — `dashboard.py` and `crm_property_detail.html` PATCH from UI. |
| POST | `/api/chain/outreach` | Emails chain estate agent to request solicitor details (dry-run unless code flag enabled). | **Staff session** + `require_nuvu_api_key()` in handler. | `jsonify` | **No in-repo caller found** — API for future/automation. |

---

### `routes/property_api.py` — `property_api_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/api/property/<prop_id>` | Returns one property JSON from same builder as dashboard. | **Staff session**. | `jsonify` | **No in-repo references** — optional/debug/integrations. |
| PATCH | `/api/sales-pipeline/<pipe_id>` | Updates `chain_status` and/or `local_authority` on `sales_pipeline`. | **Staff session**. | `jsonify` | Yes — inline JS in `dashboard.py` `DASHBOARD_HTML`. |

---

### `routes/chase_engine.py` — `chase_engine_bp`

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| POST | `/api/chase/confirmations/<cid>/confirm` | Confirms a pending chase confirmation milestone. | **Explicit** `session.get("nuvu_email")` else 401 (runs after global guard). | `jsonify` | Yes — dashboard `DASHBOARD_HTML` fetch. |
| POST | `/api/chase/confirmations/<cid>/dismiss` | Dismisses a pending confirmation. | Same. | `jsonify` | Yes — dashboard fetch. |

*Note:* `chain_chase_bp` is registered but defines **no** `@route` handlers — logic is imported from `chase_scheduler` and `progression` / `chase_engine`.

---

### `routes/portal.py` — `portal_bp` (`/portal`)

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/portal`, `/portal/` | Demo portal login page or redirect home. | Exempt (public). | `render_template_string(PORTAL_LOGIN_HTML)` or redirect | Yes — dashboard “Open portal entry”. |
| POST | `/portal/login` | Sets portal demo session from form. | Exempt. | Redirect | Yes — portal login form. |
| GET | `/portal/home` | Portal home content for logged-in demo user. | Exempt (portal session). | `render_template_string(PORTAL_HOME_HTML)` | Yes — after portal login. |
| GET | `/portal/logout` | Clears portal session. | Exempt. | Redirect | Yes — portal UI. |
| GET | `/portal/staff/property-home` | Staff-only preview of portal home for one progression row. | **Staff** (`nuvu_email`); path matched early in `require_login`. | Template string or `portal_error.html` | Yes — dashboard portal action links. |
| GET | `/portal/review/<session_id>` | Staff review of submitted answers + dispatch UI. | **Staff**; special-cased in `require_login`. | `portal_review.html` or error template | Yes — dashboard links; dispatch JS in template. |
| POST | `/portal/api/dispatch` | Generates PDF and emails solicitor via Resend when dispatch enabled. | **Staff**; special-cased in `require_login`. | `jsonify` | Yes — `portal_review.html` `fetch("/portal/api/dispatch")`. |

---

### `routes/portal_forms.py` — `portal_forms_bp` (`/portal`) and `portal_staff_api_bp` (no prefix)

| Method | Path | One sentence | Auth | Response | Used? |
|--------|------|----------------|------|----------|-------|
| GET | `/portal/form` | Seller TA6/TA10 wizard page. | Exempt (`/portal/form` prefix). | Templates / errors | Yes — emails, dashboard “View as Seller”, magic redirect. |
| GET | `/portal/form/review` | Seller-facing review / submit page. | Exempt. | Templates | Yes — dashboard links. |
| GET | `/portal/api/form-state` | JSON: form definition, responses, progress. | Exempt. | `jsonify` | Yes — `portal_form.html` client. |
| POST | `/portal/api/chat` | Anthropic Claude reply for conversational help. | Exempt. | `jsonify` | Yes — `portal_form.html`. |
| POST | `/portal/api/save-answer` | Persists one answer; may notify team on completion. | Exempt. | `jsonify` | Yes — portal form JS. |
| GET | `/portal/form/ta6_ta10` | Resolves `token` to session and redirects to wizard. | Exempt. | Redirect or error template | Yes — seller email magic links. |
| GET | `/portal/form/submitted` | Thank-you after successful submit. | Exempt. | `portal_submitted.html` or redirect | Yes — post-submit redirect from API. |
| POST | `/portal/api/submit` | Marks session submitted, updates progression, emails negotiator. | Exempt. | `jsonify` | Yes — `portal_seller_review.html` flow. |
| POST | `/api/portal/send-link` | Staff: create/resend TA6/TA10 magic link email to seller. | **Staff session** in handler; not globally exempt. | `jsonify` | Yes — `dashboard.py` and `crm_property_detail.html` `fetch`. |

---

## Templates (`templates/`)

| File | Rendered by | One-line description |
|------|-------------|----------------------|
| `crm_property_detail.html` | `crm_property_detail` | Full CRM property: milestones, notes, chases, inbound mail, chain links, portal actions. |
| `crm_cards.html` | **None** | **Orphan** — no `render_template` reference in codebase. |
| `portal/portal_base.html` | **None (directly)** | Jinja base for seller-facing portal pages. |
| `portal/portal_form.html` | `portal_form_page` | TA6/TA10 wizard UI + client JS. |
| `portal/portal_seller_review.html` | `portal_form_review_page` | Seller review of answers before submit. |
| `portal/portal_submitted.html` | `portal_form_submitted_page` | Confirmation after submission. |
| `portal/portal_error.html` | `portal.py`, `portal_forms.py` | Generic portal error / missing params. |
| `portal/portal_review.html` | `portal_review_page` | Staff review + solicitor dispatch form. |
| `portal/coming_soon.html` | `portal_forms.py` when `PORTAL_FORMS_ENABLED` is off | Service unavailable placeholder. |

**Non-file templates:** `DASHBOARD_HTML` and `LOGIN_HTML` / portal inline strings live inside `routes/dashboard.py`, `routes/auth.py`, and `routes/portal.py`.

---

## Kill switches & environment variables

| Variable | What it controls | Default | Checked in |
|----------|------------------|---------|------------|
| `WELCOME_ENGINE_ENABLED` | Sends 5 welcome emails from intake (`_send_welcome_emails`). | **false** (string compare to `"true"`) | `routes/progression.py` — `_send_welcome_emails` |
| `CHASE_ENGINE_ENABLED` | Phase A/B/C chase Resend sends via `send_chase_message` (when `outbound_enabled` is None). | **false** | `routes/chase_engine.py` — `chase_engine_sending_enabled` |
| `CHAIN_CHASE_ENABLED` | Track 6 chain solicitor sends (`chain_chase_sending_enabled` passed into `send_chase_message`). | **false** | `shared.py` — `chain_chase_sending_enabled`; used from `routes/chain_chase.py` |
| `CHASE_SCHEDULER_DISABLED` | Skips starting the 15-minute background thread. | off / empty | `utils/chase_scheduler.py` — `start_chase_cadence_scheduler` |
| `PORTAL_FORMS_ENABLED` | Seller portal pages + JSON APIs under `/portal/form` and `/portal/api/*` (except staff send-link path). | **true** | `utils/portal_config.py` — `portal_forms_enabled`; `routes/portal_forms.py` |
| `PORTAL_DISPATCH_ENABLED` | Seller magic links, `/api/submit` progression update + negotiator email, staff dispatch endpoint. | **false** | `utils/portal_config.py` — `portal_dispatch_enabled`; `portal_forms.py`, `portal.py` |
| `PORTAL_ENABLED` | Team email when seller completes all questions (`notify_team_form_completed`). | **false** | `utils/portal_config.py` — `portal_team_notifications_enabled` (reads **`PORTAL_ENABLED`**) |
| `PORTAL_DISPATCH_TEST_MODE` | Restricts solicitor dispatch recipients to internal domain or `PORTAL_DISPATCH_TEST_EMAIL`. | **true** | `utils/portal_config.py` — `portal_dispatch_test_mode`; `routes/portal_notify.py` — `_dispatch_recipient_allowed` |
| `PORTAL_AI_ENABLED` | Enables Anthropic-backed `/portal/api/chat`. | **true** | `routes/portal_forms.py` — `_portal_ai_enabled`, `api_chat` |
| `CHAIN_OUTREACH_ENABLED` | **Not an env var** — Python constant `False` in `routes/progression.py`; dry-run logs unless changed in code. | **false** (hard-coded) | `routes/progression.py` — `api_chain_outreach` |

**Config / security (not strictly kill switches but feature gates):**

| Variable | Role | Default | Where |
|----------|------|---------|-------|
| `NUVU_API_KEY` | Authenticates `/api/intake`, `/api/update`, duplicates, chain outreach handlers. | `dbe-nuvu-2026` | `shared.py` — `require_nuvu_api_key`; `routes/crm.py` for EATOC outbound header |
| `NUVU_ALLOWED_EMAILS` | Comma-separated emails allowed to request magic login links. | empty | `routes/auth.py` |
| `RESEND_API_KEY` | Resend API key. | empty | `shared.py`; also `email_engine.send_html_email` |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Supabase client (and anon path). | empty | `db_supabase.py` |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend writes when anon/RLS insufficient. | empty | `db_supabase.py` — `supabase_for_backend` |
| `FLASK_SECRET_KEY` | Flask session signing. | random if unset | `app.py` |
| `PORT` | Dev server port. | `5000` | `app.py` |
| `NUVU_BASE_URL` / `AUTH_BASE_URL` | Magic links, chase URLs, portal links. | production URL in auth | `routes/auth.py`, `routes/chase_engine.py`, `portal_forms.py`, `portal_notify.py` |
| `CHASE_TEAM_EMAIL` | Optional inbox for chase failure alerts / day-4 flags. | empty | `routes/chase_engine.py` — `_team_flag_email` |
| `PORTAL_FORM_DEMO` | Enables fixed demo session id without DB. | false | `db_portal.py` — `demo_enabled` |
| `PORTAL_DEMO_ADDRESS` / `PORTAL_DEMO_SELLER` | Demo session display fields. | example defaults | `db_portal.py` — `_demo_session` |
| `PORTAL_DISPATCH_TEST_EMAIL` | Optional single allowed non-internal email in dispatch test mode. | empty | `routes/portal_notify.py` |
| `ANTHROPIC_API_KEY` | Portal AI chat. | empty | `routes/portal_forms.py` — `_claude_messages` |

---

## External integrations

| Service | Called from | Sends / receives |
|---------|-------------|------------------|
| **Supabase (PostgREST)** | `db_supabase.py`, `db_portal.py`, route handlers | CRUD on `sales_progression`, `sales_pipeline`, `inbound_emails`, `chase_messages`, `chase_confirmations`, `chain_links`, `portal_sessions`, etc. |
| **Resend** | `routes/auth.py` (magic link); `routes/progression.py` (welcome tracks); `email_engine.send_html_email` ← `routes/chase_engine.py`, `routes/progression.py` (chain outreach when enabled); `routes/portal_notify.py` (portal lifecycle + dispatch attachments); failure copy to `CHASE_TEAM_EMAIL` from chase engine | Outbound transactional HTML (+ PDF attachment on solicitor dispatch). |
| **EATOC HTTP API** | `routes/crm.py` — `fetch_eatoc_properties`, `save_crm_note` | GET `https://app.eatoc.co.uk/api/nuvu/properties` (header `x-api-key: NUVU_API_KEY`); PATCH `…/properties/{id}` with `{ "nuvu_notes": … }`. |
| **Anthropic** | `routes/portal_forms.py` — `_claude_messages` | Messages API (`claude-haiku-4-5-20251001`) for seller form assistant. |

**Not invoked by Flask routes in this repo:** `connectors/*.py`, `scripts/*` (Alto/EATOC utilities) — documented as reference/tooling only unless separately executed.

**Inbound:** No Flask route for inbound Resend webhooks in the audited tree; email ingestion is assumed to be separate processes populating `inbound_emails` (per architecture docs).

---

## Public-access summary (no NUVU staff login)

These URLs **do not** require `nuvu_email`:

- `/static/*`
- `/login`, `/auth/verify`, `/logout`
- **`/crm` and `/crm/property/<id>`** — full live-style property data (treat as sensitive if deployed openly).
- **`POST /api/crm/notes/<prop_id>`** — also unauthenticated at Flask layer; no API key check in handler (relies on network secrecy / EATOC accepting the server key).
- `/api/intake`, `/api/update` — **API key** in handler (not a browser feature for end users).
- `/portal` demo tree and **`/portal/form*`, `/portal/api/form-state`, `/portal/api/chat`, `/portal/api/save-answer`, `/portal/api/submit`** — knowledge of `session_id` or `token` is the access control.

Everything else on the main app (including `/`, `/api/progression`, `/api/sales-pipeline`, `/api/chase/…`, `/api/portal/send-link`) expects a staff browser session unless noted.

---

## Gaps / risks flagged during audit

1. **`/api/duplicates` and `/api/chain/outreach`:** Global login guard applies first; they are **not** in `AUTH_EXEMPT_PREFIXES`, so a pure API client without session cookies cannot use them even with `X-NUVU-API-KEY`.
2. **`POST /api/crm/notes/<prop_id>`:** Public at Flask layer with no `require_nuvu_api_key` — security posture depends entirely on deployment/network and EATOC’s acceptance of the server’s `x-api-key`.
3. **`crm_cards.html`:** Unused template asset.
4. **`GET /api/property/<id>`:** No frontend references located in-repo.

---

*End of audit.*
