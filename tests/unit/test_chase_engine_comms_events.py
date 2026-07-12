"""Unit tests for chase-engine comms_sent event emission."""

from routes import chase_engine


class FakeResult:
    def __init__(self, data=None):
        self.data = data or []


class FakeInsert:
    def __init__(self, rows):
        self.rows = rows
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        self.rows.append(self.payload)
        return FakeResult([self.payload])


class FakeSupabase:
    def __init__(self):
        self.rows = {"chase_messages": []}

    def table(self, name):
        return FakeInsert(self.rows.setdefault(name, []))


def _patch_common(monkeypatch, db, events):
    monkeypatch.setattr(chase_engine, "supabase_for_backend", lambda: db)
    monkeypatch.setattr(chase_engine, "_already_sent", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        chase_engine,
        "_property_address_for_progression_id",
        lambda client, property_id: "1 High Street",
    )
    monkeypatch.setattr(chase_engine, "emit_event", lambda **event: events.append(event))


def test_dry_run_chase_emits_comms_sent(monkeypatch):
    db = FakeSupabase()
    events = []
    _patch_common(monkeypatch, db, events)
    monkeypatch.setenv("CHASE_ENGINE_ENABLED", "false")

    result = chase_engine.send_chase_message(
        property_id="progression-1",
        chase_stage="stage4_search_fees",
        chase_day=0,
        recipient_type="buyer",
        recipient_email="buyer@example.com",
        subject="Search fees",
        html_body="<p>Please confirm.</p>",
        dry_run_label="phase_b_s4_d0",
    )

    assert result is True
    assert db.rows["chase_messages"] == []
    assert len(events) == 1
    payload = events[0]["payload"]
    assert events[0]["event_type"] == "comms_sent"
    assert events[0]["property_address"] == "1 High Street"
    assert payload["dry_run"] is True
    assert payload["outcome"] == "dry_run"
    assert payload["recipient_category"] == "buyer"
    assert payload["trigger"] == "phase_b_s4_d0"
    assert payload["property_address"] == "1 High Street"


def test_governor_blocked_chase_emits_comms_sent(monkeypatch):
    db = FakeSupabase()
    events = []
    _patch_common(monkeypatch, db, events)
    monkeypatch.setattr(chase_engine, "send_html_email", lambda *args, **kwargs: "blocked:send_cap")

    result = chase_engine.send_chase_message(
        property_id="progression-1",
        chase_stage="stage5_draft_contract",
        chase_day=1,
        recipient_type="seller_solicitor",
        recipient_email="solicitor@example.com",
        subject="Draft contract",
        html_body="<p>Please update.</p>",
        outbound_enabled=True,
        dry_run_label="phase_b_s5_d1",
    )

    assert result is False
    assert db.rows["chase_messages"] == []
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["dry_run"] is False
    assert payload["outcome"] == "blocked:send_cap"
    assert payload["recipient_category"] == "seller_solicitor"
    assert payload["trigger"] == "phase_b_s5_d1"
