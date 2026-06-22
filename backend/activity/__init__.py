"""Owner Activity Center — unified, read-only aggregation of safe owner/admin
audit events across support, org/user management, marketing, and usage analytics.

This package adds NO new audit storage. It reuses the existing per-domain audit
trails (``owner_action_events`` in support, ``owner_admin_events`` in auth, the
marketing owner-action log, and the safe ``analytics_events`` feed) and exposes a
single normalized, super-admin-only endpoint: ``GET /api/owner/activity``.
"""
