"""First-party analytics spine for Ember (Owner HQ).

Stores only safe product-usage signals — event type, route, module, and coarse
marketing attribution. It deliberately never persists PHI or protected client
content (names, DOB, SSN, diagnoses, notes, messages, documents). The store is a
single additive SQLite database (``analytics.db``) that follows the project's
existing per-domain DB pattern via ``backend.shared.db_path``.
"""
