from utils import notification_log
from utils.intake_notifications import send_gate_digest


class UniqueViolation(Exception):
    pass


class FakeResult:
    def __init__(self, data=None):
        self.data = data or []


class FakeSupabase:
    def __init__(self):
        self.rows = {
            "notification_log": [],
            "intake_queue": [],
        }
        self.enforce_notification_unique = False

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.operation = "select"
        self.filters = []
        self.payload = None
        self.max_rows = None

    def select(self, _columns):
        self.operation = "select"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, count):
        self.max_rows = count
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table_name, [])
        if self.operation == "insert":
            row = dict(self.payload)
            if self.table_name == "notification_log" and self.db.enforce_notification_unique:
                for existing in rows:
                    if (
                        existing.get("agency_id") == row.get("agency_id")
                        and existing.get("content_hash") == row.get("content_hash")
                        and existing.get("sent_at", "") >= "2026-07-12T00:00:00"
                    ):
                        raise UniqueViolation("duplicate key value violates unique constraint uniq_notification_hash_v2")
            row.setdefault("id", f"row-{len(rows) + 1}")
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

        if self.max_rows is not None:
            matches = matches[: self.max_rows]
        return FakeResult(matches)


def test_send_notification_once_logs_first_send(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)

    result = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email", "sale_price"],
        "team@example.com",
        lambda: sends.append("sent"),
    )

    assert result == "sent"
    assert sends == ["sent"]
    assert len(db.rows["notification_log"]) == 1
    assert db.rows["notification_log"][0]["payload"]["status"] == "sent"


def test_send_notification_once_skips_duplicate(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)

    notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("first"),
    )
    result = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("second"),
    )

    assert result == "duplicate_skipped"
    assert sends == ["first"]
    assert len(db.rows["notification_log"]) == 1


def test_send_notification_once_unique_violation_skips_concurrent_duplicate(monkeypatch):
    db = FakeSupabase()
    db.enforce_notification_unique = True
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)
    monkeypatch.setattr(notification_log, "_notification_exists", lambda *args, **kwargs: False)

    first = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("first"),
    )
    second = notification_log.send_notification_once(
        "2 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("second"),
    )

    assert first == "sent"
    assert second == "duplicate_skipped"
    assert sends == ["first"]
    assert len(db.rows["notification_log"]) == 1


def test_send_notification_once_reserved_row_blocks_after_crash(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)
    content = ["buyer_email"]
    db.rows["notification_log"].append(
        {
            "id": "row-crash",
            "agency_id": "dbe",
            "property_address": "1 High Street",
            "notification_type": "gate_blocked",
            "content_hash": notification_log._content_hash(content),
            "recipient": "team@example.com",
            "sent_at": "2026-07-12T09:00:00+00:00",
            "payload": {"status": "reserved", "content": content},
        }
    )

    result = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        content,
        "team@example.com",
        lambda: sends.append("second"),
    )

    assert result == "duplicate_skipped"
    assert sends == []
    assert len(db.rows["notification_log"]) == 1


def test_send_notification_once_historical_hash_blocks_even_before_partial_index(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)
    content = ["buyer_email"]
    db.rows["notification_log"].append(
        {
            "id": "row-history",
            "agency_id": "dbe",
            "property_address": "Old Property",
            "notification_type": "gate_blocked",
            "content_hash": notification_log._content_hash(content),
            "recipient": "team@example.com",
            "sent_at": "2026-07-10T09:00:00+00:00",
            "payload": {"status": "sent", "content": content},
        }
    )

    result = notification_log.send_notification_once(
        "New Property",
        "gate_blocked",
        content,
        "team@example.com",
        lambda: sends.append("new"),
    )

    assert result == "duplicate_skipped"
    assert sends == []
    assert len(db.rows["notification_log"]) == 1


def test_send_notification_once_allows_changed_missing_fields(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)

    notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("first"),
    )
    result = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email", "sale_price"],
        "team@example.com",
        lambda: sends.append("second"),
    )

    assert result == "sent"
    assert sends == ["first", "second"]
    assert len(db.rows["notification_log"]) == 2


def test_send_notification_once_survives_queue_wipe(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setattr(notification_log, "_client", lambda: db)

    notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("first"),
    )
    db.rows["intake_queue"].clear()
    result = notification_log.send_notification_once(
        "1 High Street",
        "gate_blocked",
        ["buyer_email"],
        "team@example.com",
        lambda: sends.append("second"),
    )

    assert result == "duplicate_skipped"
    assert sends == ["first"]
    assert len(db.rows["notification_log"]) == 1


def test_gate_digest_sends_once_and_logs_properties(monkeypatch):
    db = FakeSupabase()
    sends = []
    monkeypatch.setenv("NOTIFICATION_EMAIL", "team@example.com")
    monkeypatch.setattr(notification_log, "_client", lambda: db)
    monkeypatch.setattr("utils.intake_notifications._mark_notification_sent", lambda _addr: None)

    candidates = [
        {
            "property_address": f"{idx} High Street",
            "gate_status": "blocked",
            "property_data": {},
            "missing_fields": ["buyer_email", f"field_{idx}"],
            "tiers": {"1a": False, "1b": True, "1c": True, "1d": True},
        }
        for idx in range(1, 6)
    ]

    send_gate_digest(candidates, send_fn=lambda message: sends.append(message))

    assert len(sends) == 1
    assert len(db.rows["notification_log"]) == 6
    property_rows = [
        row for row in db.rows["notification_log"]
        if row["notification_type"] == "gate_blocked"
    ]
    assert len(property_rows) == 5
    assert all(row["payload"]["included_in_digest"] is True for row in property_rows)
