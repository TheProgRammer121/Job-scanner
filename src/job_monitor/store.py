from __future__ import annotations

import os

from .database import Database
from .supabase import SupabaseDatabase


def create_store():
    """Use persistent Supabase storage when both server-side settings exist."""
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseDatabase(url, key)
    return Database()
