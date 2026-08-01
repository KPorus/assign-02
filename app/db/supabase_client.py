"""Supabase clients (Auth + public.users profiles).

Keep admin/table ops on a dedicated service-role client. Never call
sign_in_with_password on that client — it would replace the service role
session and break admin.create_user ("User not allowed").
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


def _settings_or_raise() -> tuple[str, str]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the environment"
        )
    return settings.supabase_url, settings.supabase_key


@lru_cache
def get_supabase() -> Client:
    """Service-role client for admin Auth + table CRUD (no user sign-in)."""
    url, key = _settings_or_raise()
    return create_client(url, key)


def create_auth_client() -> Client:
    """Ephemeral client for password login / token checks only."""
    url, key = _settings_or_raise()
    return create_client(url, key)
