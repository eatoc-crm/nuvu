import os

import resend

# Centralised config used by multiple blueprints.
resend.api_key = os.environ.get("RESEND_API_KEY", "")

# Shared Supabase client (initialised inside db_supabase.py).
from db_supabase import supabase as sb  # noqa: E402

