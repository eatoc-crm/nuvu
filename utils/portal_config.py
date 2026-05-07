"""Kill switches and flags for the TA6/TA10 portal (Window 3)."""

from __future__ import annotations

import os


def env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def portal_forms_enabled() -> bool:
    """Seller-facing form UI and save API. Default on for local dev."""
    return env_bool("PORTAL_FORMS_ENABLED", "true")


def portal_team_notifications_enabled() -> bool:
    """Resend email to sales progression when a form is completed. Default off."""
    return env_bool("PORTAL_ENABLED", "false")


def portal_dispatch_enabled() -> bool:
    """Approve & dispatch to solicitor. Default off."""
    return env_bool("PORTAL_DISPATCH_ENABLED", "false")


def portal_dispatch_test_mode() -> bool:
    """When true (default), only internal @brittonestates.co.uk recipients are allowed."""
    return env_bool("PORTAL_DISPATCH_TEST_MODE", "true")
