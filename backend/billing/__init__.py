"""Billing + plan-limits foundation (Stripe-disabled).

This package holds the *internal* subscription model: a static plan catalog,
pure pricing/recommendation helpers, and the FastAPI router for reading an org's
billing status. There is deliberately NO Stripe SDK, no API keys, no checkout,
and no live payment action anywhere in this package — Stripe IDs are stored as
inert placeholder columns so the integration can be plugged in later.
"""
