from flask import Flask, session

from routes import intake, intake_queue
from routes import progression


class FakeResult:
    def __init__(self, data=None):
        self.data = data or []


class FakeSupabase:
    def __init__(self):
        self.rows = {
            "intake_queue": [],
            "sales_pipeline": [],
            "sales_progression": [],
            "send_log": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.operation = "select"
        self.filters = []
        self.payload = None

    def select(self, _columns):
        self.operation = "select"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def upsert(self, payload, on_conflict=None):
        self.operation = "upsert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table_name, [])
        if self.operation == "upsert":
            row = dict(self.payload)
            address = row.get("property_address")
            for existing in rows:
                if existing.get("property_address") == address:
                    existing.update(row)
                    return FakeResult([existing])
            rows.append(row)
            return FakeResult([row])

        matches = [
            row
            for row in rows
            if all(row.get(key) == value for key, value in self.filters)
        ]

        if self.operation == "update":
            for row in matches:
                row.update(self.payload)
            return FakeResult(matches)

        return FakeResult(matches)


def test_api_intake_does_not_trigger_welcome_send(monkeypatch):
    db = FakeSupabase()
    welcome_calls = []
    app = Flask(__name__)
    monkeypatch.setattr(intake, "require_nuvu_api_key", lambda: None)
    monkeypatch.setattr(intake, "eatoc_post", lambda path, body: None)
    monkeypatch.setattr(intake, "sb", db)
    monkeypatch.setattr("db_supabase.supabase_for_backend", lambda: db)
    monkeypatch.setattr(
        "routes.progression._send_welcome_emails",
        lambda *args, **kwargs: welcome_calls.append((args, kwargs)),
    )

    payload = {
        "property_address": "1 High Street",
        "status": "Under Offer",
        "buyer_name": "Buyer",
        "buyer_email": "buyer@example.com",
        "vendor_name": "Seller",
        "vendor_email": "seller@example.com",
    }
    with app.test_request_context("/api/intake", method="POST", json=payload):
        response, status = intake.api_intake()

    assert status == 200
    assert response.get_json()["success"] is True
    assert welcome_calls == []
    assert db.rows["send_log"] == []


def test_intake_approval_triggers_welcome_with_intake_approved(monkeypatch):
    db = FakeSupabase()
    db.rows["intake_queue"].append(
        {"property_address": "1 High Street", "gate_status": "ready"}
    )
    db.rows["sales_pipeline"].append(
        {
            "property_address": "1 High Street",
            "buyers_solicitor_email": "buyer-sol@example.com",
        }
    )
    db.rows["sales_progression"].append(
        {
            "property_address": "1 High Street",
            "buyer_email": "buyer@example.com",
            "vendor_email": "seller@example.com",
        }
    )
    welcome_calls = []
    events = []
    app = Flask(__name__)
    app.secret_key = "test"
    monkeypatch.setattr(intake_queue, "supabase_for_backend", lambda: db)
    monkeypatch.setattr(intake_queue, "emit_event", lambda **event: events.append(event))
    monkeypatch.setattr(
        "routes.progression._send_welcome_emails",
        lambda data, trigger=None: welcome_calls.append((data, trigger)),
    )

    with app.test_request_context("/intake-queue/approve/1 High Street", method="POST"):
        session["nuvu_email"] = "staff@example.com"
        response = intake_queue.intake_queue_approve("1 High Street")

    assert response.status_code == 302
    assert db.rows["intake_queue"][0]["gate_status"] == "approved"
    assert len(welcome_calls) == 1
    data, trigger = welcome_calls[0]
    assert trigger == "intake_approved"
    assert data["buyer_email"] == "buyer@example.com"
    assert data["buyers_solicitor_email"] == "buyer-sol@example.com"
    assert events[0]["event_type"] == "human_decision"


def test_welcome_attempt_emits_comms_sent_with_approval_trigger(monkeypatch):
    events = []
    governed_calls = []
    monkeypatch.setenv("WELCOME_ENGINE_ENABLED", "true")
    monkeypatch.setattr(
        progression,
        "governed_send",
        lambda *args, **kwargs: governed_calls.append((args, kwargs)) or "blocked:kill_switch_category",
    )
    monkeypatch.setattr(progression, "emit_event", lambda **event: events.append(event))

    progression._send_welcome_emails(
        {
            "property_address": "1 High Street",
            "buyer_email": "buyer@example.com",
            "buyer_name": "Buyer",
        },
        trigger="intake_approved",
    )

    assert len(governed_calls) == 1
    assert len(events) == 1
    assert events[0]["event_type"] == "comms_sent"
    assert events[0]["property_address"] == "1 High Street"
    assert events[0]["payload"]["trigger"] == "intake_approved"
    assert events[0]["payload"]["outcome"] == "blocked:kill_switch_category"
