"""Support Queue storage + routing package (Owner HQ).

A safe, internal support-ticket system. Customers/users file tickets; the platform
owner (super-admin) triages them from Ember HQ. No protected client content (PHI)
is ever stored — see ``backend.support.store`` for the sanitization rules.
"""
