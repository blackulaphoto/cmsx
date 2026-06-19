"""Multi-tenancy foundation helpers (Phase 0).

This module introduces the seam that all future multi-tenant logic pivots on.
While ``MULTI_TENANT_ENABLED`` is false (the default), the system behaves as a
single-agency app: every request resolves to the single ``DEFAULT_ORG_ID``.

Nothing in this module enforces isolation yet. It only provides:
  - the default-org identifier used for backfill and one-org mode,
  - a flag reader, and
  - an org resolver that callers will use in later phases.
"""
from __future__ import annotations

import os
from typing import Any

# The single tenant that every existing row is backfilled into. While
# multi-tenancy is disabled, all users and data resolve to this org.
DEFAULT_ORG_ID = "org_default"
DEFAULT_ORG_NAME = "Default Organization"

# Mirror the truthy-value convention already used elsewhere in the codebase
# (see backend/auth/service.py TRUE_VALUES).
_TRUE_VALUES = {"1", "true", "yes", "on"}


def multi_tenant_enabled() -> bool:
    """Return True only when MULTI_TENANT_ENABLED is explicitly turned on.

    Defaults to False so the app keeps its current single-agency behavior.
    """
    return (os.getenv("MULTI_TENANT_ENABLED") or "").strip().lower() in _TRUE_VALUES


def resolve_org_id(user: Any) -> str:
    """Resolve the effective organization id for a request/user.

    - When multi-tenancy is disabled: always returns ``DEFAULT_ORG_ID`` so
      every request stays inside the single default org (one-org mode).
    - When enabled: returns the user's ``org_id`` if present, otherwise falls
      back to ``DEFAULT_ORG_ID`` to remain safe rather than raising.
    """
    if not multi_tenant_enabled():
        return DEFAULT_ORG_ID

    org_id = getattr(user, "org_id", None)
    if isinstance(org_id, str) and org_id.strip():
        return org_id.strip()
    return DEFAULT_ORG_ID
