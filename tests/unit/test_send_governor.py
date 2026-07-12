import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

from utils import notification_log, send_governor


class FakeResult:
    def __init__(self, data=None):
        self.data = data or []


class FakeSupabase:
    def __init__(self):
        self.rows = {
            "send_log": [],
            "notification_log": [],
            "sales_pipeline": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.operation = "select"
        self.filters = []
        self.gte_filters = []
        self.payload = None
        self.max_rows = None

    def select(self, _columns):
        self.operation = "select"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def gte(self, key, value):
        self.gte_filters.append((key, value))
        return self

    def limit(self, count):
        self.max_rows = count
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table_name, [])
        if self.operation == "insert":
            row = dict(self.payload)
            row.setdefault("id", f"{self.table_name}-{len(rows) + 1}")
            rows.append(row)
            return FakeResult([row])

        matches = [
            row
            for row in rows
            if all(row.get(key) == value for key, value in self.filters)
            and all(str(row.get(key) or "") >= str(value) for key, value in self.gte_filters)
        ]
        if self.max_rows is not None:
            matches = matches[: self.max_rows]
        return FakeResult(matches)


def _setup(monkeypatch, db, sends, now):
    monkeypatch.setattr(send_governor, "_client", lambda: db)
    monkeypatch.setattr(notification_log, "_client", lambda: db)
    monkeypatch.setattr(send_governor, "_now", lambda: now)
    monkeypatch.setattr(
        send_governor.resend.Emails,
        "send",
        lambda payload: sends.append(payload) or {"id": f"send-{len(sends)}"},
    )
    monkeypatch.setenv("SEND_GOVERNOR_ENABLED", "true")
    monkeypatch.setenv("SEND_CATEGORY_NOTIFICATIONS", "true")
    monkeypatch.setenv("SEND_CATEGORY_WELCOME", "true")
    monkeypatch.setenv("SEND_CATEGORY_CHASE", "true")
    monkeypatch.setenv("SEND_CATEGORY_PORTAL", "true")
    monkeypatch.setenv("SEND_CAP_PER_HOUR", "30")
    monkeypatch.setenv("SEND_CAP_PER_DAY", "100")
    monkeypatch.setenv("NOTIFICATION_EMAIL", "david@example.com")


def test_category_switch_off_blocks_and_logs(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_CATEGORY_PORTAL", "false")

    result = send_governor.governed_send("portal", "seller@example.com", "Subject", "<p>Body</p>")

    assert result == "blocked:kill_switch_category"
    assert sends == []
    assert db.rows["send_log"][0]["outcome"] == "blocked:kill_switch_category"


def test_master_switch_off_blocks_system_too(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_GOVERNOR_ENABLED", "false")

    normal = send_governor.governed_send("notifications", "team@example.com", "A", "<p>A</p>")
    system = send_governor.governed_send("system", "team@example.com", "B", "<p>B</p>")

    assert normal == "blocked:kill_switch_global"
    assert system == "blocked:kill_switch_global"
    assert sends == []
    assert [row["outcome"] for row in db.rows["send_log"]] == [
        "blocked:kill_switch_global",
        "blocked:kill_switch_global",
    ]


def test_hourly_cap_blocks_after_cap_and_sends_one_alert(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_CAP_PER_HOUR", "3")
    monkeypatch.setenv("SEND_CAP_PER_DAY", "99")

    results = [
        send_governor.governed_send("notifications", f"{idx}@example.com", "Subject", "<p>Body</p>")
        for idx in range(8)
    ]

    assert results.count("sent") == 3
    assert results.count("blocked:hourly_cap") == 5
    assert len([row for row in db.rows["notification_log"] if row["notification_type"] == "governor_cap_alert"]) == 1
    assert len([payload for payload in sends if payload["subject"].startswith("NUVU Send Governor cap hit")]) == 1


def test_daily_cap_blocks_after_cap_and_sends_one_alert(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_CAP_PER_HOUR", "99")
    monkeypatch.setenv("SEND_CAP_PER_DAY", "3")

    results = [
        send_governor.governed_send("notifications", f"{idx}@example.com", "Subject", "<p>Body</p>")
        for idx in range(8)
    ]

    assert results.count("sent") == 3
    assert results.count("blocked:daily_cap") == 5
    assert len([row for row in db.rows["notification_log"] if row["notification_type"] == "governor_cap_alert"]) == 1
    assert len([payload for payload in sends if payload["subject"].startswith("NUVU Send Governor cap hit")]) == 1


def test_blocked_attempts_are_in_send_log(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_CATEGORY_WELCOME", "false")

    send_governor.governed_send("welcome", "buyer@example.com", "Welcome", "<p>Hello</p>")

    assert db.rows["send_log"] == [
        {
            "agency_id": "dbe",
            "category": "welcome",
            "recipient": "buyer@example.com",
            "subject": "Welcome",
            "outcome": "blocked:kill_switch_category",
            "attempted_at": now.isoformat(),
            "metadata": None,
            "id": "send_log-1",
        }
    ]


def test_do_not_chase_blocks_flagged_chase_addresses(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    flagged = [
        "Plot at Culgaith",
        "Romanway Irthington, CA6 4NF",
        "The Barns at Albyfield",
    ]
    db.rows["sales_pipeline"] = [
        {"property_address": addr, "do_not_chase": True}
        for addr in flagged
    ]

    results = [
        send_governor.governed_send(
            "chase",
            "buyer@example.com",
            "Chase",
            "<p>Body</p>",
            property_address=addr,
        )
        for addr in flagged
    ]

    assert results == ["blocked:do_not_chase"] * 3
    assert sends == []
    assert [row["outcome"] for row in db.rows["send_log"]] == ["blocked:do_not_chase"] * 3


def test_do_not_chase_allows_non_flagged_property(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    db.rows["sales_pipeline"].append(
        {"property_address": "1 High Street", "do_not_chase": False}
    )

    result = send_governor.governed_send(
        "chase",
        "buyer@example.com",
        "Chase",
        "<p>Body</p>",
        property_address="1 High Street",
    )

    assert result == "sent"
    assert len(sends) == 1


def test_do_not_chase_lookup_failure_blocks_chase(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)

    result = send_governor.governed_send(
        "chase",
        "buyer@example.com",
        "Chase",
        "<p>Body</p>",
        property_address="Missing Address",
    )

    assert result == "blocked:do_not_chase_lookup_failed"
    assert sends == []
    assert db.rows["send_log"][0]["outcome"] == "blocked:do_not_chase_lookup_failed"


def test_do_not_chase_blocks_welcome_category(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    db.rows["sales_pipeline"].append(
        {"property_address": "The Barns at Albyfield", "do_not_chase": True}
    )

    result = send_governor.governed_send(
        "welcome",
        "seller@example.com",
        "Welcome",
        "<p>Body</p>",
        property_address="The Barns at Albyfield",
    )

    assert result == "blocked:do_not_chase"
    assert sends == []


def test_do_not_chase_does_not_block_notifications(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    db.rows["sales_pipeline"].append(
        {"property_address": "Plot at Culgaith", "do_not_chase": True}
    )

    result = send_governor.governed_send(
        "notifications",
        "team@example.com",
        "Alert",
        "<p>Body</p>",
        property_address="Plot at Culgaith",
    )

    assert result == "sent"
    assert len(sends) == 1


def test_hourly_cap_uses_rolling_window(monkeypatch):
    db = FakeSupabase()
    sends = []
    now = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    _setup(monkeypatch, db, sends, now)
    monkeypatch.setenv("SEND_CAP_PER_HOUR", "1")
    monkeypatch.setenv("SEND_CAP_PER_DAY", "99")
    db.rows["send_log"].append(
        {
            "agency_id": "dbe",
            "category": "notifications",
            "recipient": "old@example.com",
            "subject": "Old",
            "outcome": "sent",
            "attempted_at": (now - timedelta(hours=2)).isoformat(),
            "metadata": None,
        }
    )

    result = send_governor.governed_send("notifications", "new@example.com", "New", "<p>New</p>")

    assert result == "sent"


def test_resend_imported_only_in_send_governor():
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for path in root.rglob("*.py"):
        if (
            ".git" in path.parts
            or ".venv" in path.parts
            or "venv" in path.parts
            or "__pycache__" in path.parts
            or path == root / "utils" / "send_governor.py"
        ):
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(alias.name == "resend" for alias in node.names):
                offenders.append(str(path.relative_to(root)))
                break
            if isinstance(node, ast.ImportFrom) and node.module == "resend":
                offenders.append(str(path.relative_to(root)))
                break
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "send"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "Emails"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "resend"
            ):
                offenders.append(str(path.relative_to(root)))
                break

    assert offenders == []
