from __future__ import annotations

import json
import logging
import os
import sqlite3
import base64
import uuid
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from fastapi import HTTPException, Request, status
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)

from backend.shared.db_path import DB_DIR
from backend.shared.tenancy import DEFAULT_ORG_ID, DEFAULT_ORG_NAME
from backend.billing import plans as billing_plans
AUTH_DB_PATH = DB_DIR / "auth.db"
ADMIN_ROLE = "admin"
CASE_MANAGER_ROLE = "case_manager"
ALLOWED_ROLES = {ADMIN_ROLE, CASE_MANAGER_ROLE}
ORG_ADMIN_ROLE = "org_admin"
ORG_MEMBER_ROLE = "member"
BOOTSTRAP_ADMIN_EMAILS = {"blackulaphotography@gmail.com"}
# Platform owner / super-admin allowlist — DISTINCT from org admins. Only these
# accounts may reach the Super Admin Panel. Extend via PLATFORM_SUPER_ADMIN_EMAILS
# (comma-separated env). Never grant this to every org admin.
PLATFORM_SUPER_ADMIN_EMAILS = {"blackulaphotography@gmail.com"}
TRUE_VALUES = {"1", "true", "yes", "on"}
# Org types offered in first-login onboarding ("individual" is the personal
# workspace created behind the scenes; the rest are explicit org choices).
ALLOWED_ORG_TYPES = {
    "treatment_center",
    "sober_living",
    "case_management_agency",
    "independent_provider",
    "other",
    "individual",
}
TEST_AUTH_ENVIRONMENTS = {"test", "testing", "e2e"}
PRODUCTION_ENVIRONMENTS = {"prod", "production"}


@dataclass
class AuthenticatedUser:
    firebase_uid: str
    email: str
    full_name: str
    role: str
    case_manager_id: str
    auth_provider: str
    is_active: bool
    # Multi-tenancy foundation (Phase 0). Defaults keep all existing
    # keyword constructions working unchanged; while MULTI_TENANT_ENABLED is
    # false these values are not used for any isolation decision.
    org_id: str = DEFAULT_ORG_ID
    org_role: str = ORG_MEMBER_ROLE
    # First-login onboarding (org/workspace setup). Defaults True so every
    # directly-constructed user (tests, test-auth) is treated as already
    # configured; only profiles freshly inserted by the auth store start False.
    onboarding_completed: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN_ROLE


class FirebaseAuthService:
    def __init__(self, db_path: Path = AUTH_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._firebase_app: Optional[firebase_admin.App] = None
        self._initialize_profile_store()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_profile_store(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firebase_uid TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'case_manager',
                    case_manager_id TEXT NOT NULL UNIQUE,
                    auth_provider TEXT NOT NULL DEFAULT 'password',
                    photo_url TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_profiles_case_manager_id ON user_profiles(case_manager_id)"
            )

            # ── Multi-tenancy foundation (Phase 0) ──────────────────────────
            # Additive only. Tables/columns are created idempotently and all
            # existing data is backfilled into a single default org so the app
            # keeps its current single-agency behavior while
            # MULTI_TENANT_ENABLED is false.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    org_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    plan TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invites (
                    invite_id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    org_role TEXT NOT NULL DEFAULT 'member',
                    token TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_invites_email_status ON invites(email, status)"
            )

            profile_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(user_profiles)").fetchall()
            }
            if "org_id" not in profile_columns:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN org_id TEXT")
            if "org_role" not in profile_columns:
                conn.execute(
                    "ALTER TABLE user_profiles ADD COLUMN org_role TEXT NOT NULL DEFAULT 'member'"
                )
            # First-login onboarding flag. Added with DEFAULT 0, then every row
            # present at migration time is marked complete (1) — existing users
            # are already configured and must NOT be sent back through onboarding.
            # Only NEW rows inserted after this migration start at 0.
            if "onboarding_completed" not in profile_columns:
                conn.execute(
                    "ALTER TABLE user_profiles ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0"
                )
                conn.execute("UPDATE user_profiles SET onboarding_completed = 1")

            # Organization metadata (org type + creator) for onboarding-created orgs.
            org_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(organizations)").fetchall()
            }
            if "org_type" not in org_columns:
                conn.execute("ALTER TABLE organizations ADD COLUMN org_type TEXT")
            if "created_by" not in org_columns:
                conn.execute("ALTER TABLE organizations ADD COLUMN created_by TEXT")

            # ── Billing + plan-limits foundation (Stripe-disabled) ──────────
            # Additive/idempotent only. These columns hold the *internal*
            # subscription model; the stripe_* columns are inert placeholders
            # (always NULL until a future Stripe integration is wired). No
            # Stripe SDK, keys, or live billing logic touch this migration.
            billing_columns = [
                ("billing_status", "TEXT"),
                ("plan_code", "TEXT"),
                ("trial_ends_at", "TEXT"),
                ("subscription_provider", "TEXT"),
                ("stripe_customer_id", "TEXT"),
                ("stripe_subscription_id", "TEXT"),
                ("plan_limits", "TEXT"),
            ]
            for col_name, col_type in billing_columns:
                if col_name not in org_columns:
                    conn.execute(
                        f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}"
                    )

            # Invite lifecycle metadata for team management (all additive).
            invite_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(invites)").fetchall()
            }
            if "invited_by" not in invite_columns:
                conn.execute("ALTER TABLE invites ADD COLUMN invited_by TEXT")
            if "accepted_at" not in invite_columns:
                conn.execute("ALTER TABLE invites ADD COLUMN accepted_at TEXT")
            if "cancelled_at" not in invite_columns:
                conn.execute("ALTER TABLE invites ADD COLUMN cancelled_at TEXT")
            if "invited_name" not in invite_columns:
                conn.execute("ALTER TABLE invites ADD COLUMN invited_name TEXT")

            conn.commit()
            self._seed_default_org(conn)
            self._backfill_user_orgs(conn)
            self._backfill_org_billing(conn)
            conn.commit()

    def _seed_default_org(self, conn: sqlite3.Connection) -> None:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO organizations (org_id, name, status, plan, created_at, updated_at)
            VALUES (?, ?, 'active', NULL, ?, ?)
            """,
            (DEFAULT_ORG_ID, DEFAULT_ORG_NAME, now, now),
        )

    def _admin_emails(self) -> set:
        emails = {
            item.strip().lower()
            for item in (os.getenv("AUTH_ADMIN_EMAILS") or "").split(",")
            if item.strip()
        }
        emails.update(BOOTSTRAP_ADMIN_EMAILS)
        return emails

    def _backfill_user_orgs(self, conn: sqlite3.Connection) -> None:
        # Any existing profile without an org joins the default org.
        conn.execute(
            "UPDATE user_profiles SET org_id = ? WHERE org_id IS NULL OR TRIM(org_id) = ''",
            (DEFAULT_ORG_ID,),
        )
        # Bootstrap/allowlist admins become org admins of the default org.
        admin_emails = self._admin_emails()
        if admin_emails:
            placeholders = ",".join("?" for _ in admin_emails)
            conn.execute(
                f"""
                UPDATE user_profiles
                SET org_role = '{ORG_ADMIN_ROLE}'
                WHERE LOWER(email) IN ({placeholders})
                """,
                tuple(admin_emails),
            )

    def _backfill_org_billing(self, conn: sqlite3.Connection) -> None:
        """Stamp default billing state onto any org missing it (idempotent).

        Existing orgs are placed on the free trial so the app keeps working with
        no live billing. Only NULL/blank fields are touched — a billing state set
        manually by a super-admin is never overwritten. No Stripe values are
        ever written here (the stripe_* columns stay NULL placeholders).
        """
        now = datetime.utcnow()
        trial_ends = (now + timedelta(days=billing_plans.DEFAULT_TRIAL_DAYS)).isoformat()
        conn.execute(
            """
            UPDATE organizations
            SET billing_status = ?
            WHERE billing_status IS NULL OR TRIM(billing_status) = ''
            """,
            (billing_plans.DEFAULT_BILLING_STATUS,),
        )
        conn.execute(
            """
            UPDATE organizations
            SET plan_code = ?
            WHERE plan_code IS NULL OR TRIM(plan_code) = ''
            """,
            (billing_plans.DEFAULT_PLAN_CODE,),
        )
        conn.execute(
            """
            UPDATE organizations
            SET trial_ends_at = ?
            WHERE (trial_ends_at IS NULL OR TRIM(trial_ends_at) = '')
              AND billing_status = ?
            """,
            (trial_ends, billing_plans.DEFAULT_BILLING_STATUS),
        )

    def _get_firebase_app(self) -> firebase_admin.App:
        if self._firebase_app is not None:
            return self._firebase_app

        if firebase_admin._apps:
            self._firebase_app = firebase_admin.get_app()
            return self._firebase_app

        service_account_json = (os.getenv("FIREBASE_ADMIN_SERVICE_ACCOUNT_JSON") or "").strip()
        service_account_path = (os.getenv("FIREBASE_ADMIN_SERVICE_ACCOUNT_PATH") or "").strip()

        cred = None
        if service_account_json:
            cred = credentials.Certificate(json.loads(service_account_json))
        elif service_account_path:
            cred = credentials.Certificate(service_account_path)
        else:
            raise RuntimeError(
                "Firebase Admin credentials are not configured. "
                "Set FIREBASE_ADMIN_SERVICE_ACCOUNT_JSON or FIREBASE_ADMIN_SERVICE_ACCOUNT_PATH."
            )

        options: Dict[str, Any] = {}
        project_id = (
            os.getenv("VITE_FIREBASE_PROJECT_ID")
            or os.getenv("NEXT_PUBLIC_FIREBASE_PROJECT_ID")
            or os.getenv("FIREBASE_PROJECT_ID")
            or ""
        ).strip()
        if project_id:
            options["projectId"] = project_id

        self._firebase_app = firebase_admin.initialize_app(cred, options or None)
        return self._firebase_app

    def _get_project_id(self) -> str:
        project_id = (
            os.getenv("VITE_FIREBASE_PROJECT_ID")
            or os.getenv("NEXT_PUBLIC_FIREBASE_PROJECT_ID")
            or os.getenv("FIREBASE_PROJECT_ID")
            or ""
        ).strip()
        return project_id

    def _get_project_id_from_token(self, token: str) -> str:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Malformed JWT")
            payload = parts[1]
            payload += "=" * (-len(payload) % 4)
            decoded_payload = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
            audience = (decoded_payload.get("aud") or "").strip()
            if audience:
                return audience
            issuer = (decoded_payload.get("iss") or "").strip().rstrip("/")
            if issuer:
                return issuer.rsplit("/", 1)[-1]
        except Exception as exc:
            logger.warning("Could not infer Firebase project ID from token: %s", exc)
        return ""

    def _verify_token_with_public_certs(self, token: str) -> Dict[str, Any]:
        try:
            request_adapter = google_auth_requests.Request()
            project_id = self._get_project_id() or self._get_project_id_from_token(token)
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Firebase project ID is not configured on the backend",
                )
            decoded = google_id_token.verify_firebase_token(
                token,
                request_adapter,
                audience=project_id,
            )
            if not decoded:
                raise ValueError("Decoded Firebase token was empty")
            return decoded
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Public-cert Firebase token verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token",
            ) from exc

    def verify_bearer_token(self, authorization_header: Optional[str]) -> Dict[str, Any]:
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Firebase bearer token",
            )

        token = authorization_header.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Firebase bearer token",
            )

        try:
            try:
                self._get_firebase_app()
                return firebase_auth.verify_id_token(token)
            except RuntimeError as exc:
                logger.info("Firebase Admin credentials unavailable, falling back to public-cert verification: %s", exc)
                return self._verify_token_with_public_certs(token)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Firebase token verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token",
            ) from exc

    def _default_case_manager_id(self, firebase_uid: str) -> str:
        return firebase_uid

    def _role_for_email(self, email: str) -> str:
        admin_emails = {
            item.strip().lower()
            for item in (os.getenv("AUTH_ADMIN_EMAILS") or "").split(",")
            if item.strip()
        }
        admin_emails.update(BOOTSTRAP_ADMIN_EMAILS)
        return ADMIN_ROLE if email.strip().lower() in admin_emails else CASE_MANAGER_ROLE

    def get_profile_by_uid(self, firebase_uid: str) -> Optional[AuthenticatedUser]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def get_profile_by_case_manager_id(self, case_manager_id: str) -> Optional[AuthenticatedUser]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE case_manager_id = ?",
                (case_manager_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def upsert_profile_from_token(
        self,
        decoded_token: Dict[str, Any],
        requested_role: Optional[str] = None,
        requested_case_manager_id: Optional[str] = None,
    ) -> AuthenticatedUser:
        firebase_uid = (
            decoded_token.get("uid")
            or decoded_token.get("user_id")
            or decoded_token.get("sub")
            or ""
        ).strip()
        if not firebase_uid:
            raise HTTPException(status_code=400, detail="Firebase token is missing a user identifier")
        email = (decoded_token.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="Firebase user is missing an email address")

        name = (
            decoded_token.get("name")
            or decoded_token.get("display_name")
            or email.split("@", 1)[0]
        ).strip()
        provider = "password"
        firebase_claims = decoded_token.get("firebase") or {}
        sign_in_provider = firebase_claims.get("sign_in_provider")
        if sign_in_provider:
            provider = sign_in_provider

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()

            if existing:
                current_role = existing["role"]
                role = current_role
                role_from_email = self._role_for_email(email)
                if role_from_email == ADMIN_ROLE:
                    role = ADMIN_ROLE
                elif requested_role and requested_role in ALLOWED_ROLES and requested_role != role:
                    if current_role != ADMIN_ROLE:
                        role = requested_role
                case_manager_id = existing["case_manager_id"]
                if requested_case_manager_id and role == ADMIN_ROLE:
                    case_manager_id = requested_case_manager_id.strip()
                # Preserve any existing org assignment; never leave it null.
                existing_org_id = (existing["org_id"] or "").strip()
                org_id = existing_org_id or DEFAULT_ORG_ID
                existing_org_role = (existing["org_role"] or ORG_MEMBER_ROLE).strip()
                org_role = ORG_ADMIN_ROLE if role == ADMIN_ROLE else existing_org_role
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    UPDATE user_profiles
                    SET email = ?, full_name = ?, role = ?, case_manager_id = ?, auth_provider = ?, photo_url = ?, updated_at = ?, last_login_at = ?, org_id = ?, org_role = ?
                    WHERE firebase_uid = ?
                    """,
                    (
                        email,
                        name,
                        role,
                        case_manager_id,
                        provider,
                        decoded_token.get("picture") or "",
                        now,
                        now,
                        org_id,
                        org_role,
                        firebase_uid,
                    ),
                )
                conn.commit()
                refreshed = conn.execute(
                    "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                    (firebase_uid,),
                ).fetchone()
                return self._row_to_user(refreshed)

            role = requested_role if requested_role in ALLOWED_ROLES else self._role_for_email(email)
            case_manager_id = (
                requested_case_manager_id.strip()
                if requested_case_manager_id and role == ADMIN_ROLE
                else self._default_case_manager_id(firebase_uid)
            )
            # New users are stamped into the default org (one-org mode).
            org_id = DEFAULT_ORG_ID
            org_role = ORG_ADMIN_ROLE if role == ADMIN_ROLE else ORG_MEMBER_ROLE
            now = datetime.utcnow().isoformat()
            # Brand-new users start onboarding_completed = 0 so the front door
            # routes them to first-login onboarding. They are stamped into the
            # default org for now (harmless while MULTI_TENANT_ENABLED=false);
            # onboarding reassigns org_id/org_role once they choose a workspace.
            conn.execute(
                """
                INSERT INTO user_profiles (
                    firebase_uid, email, full_name, role, case_manager_id, auth_provider,
                    photo_url, is_active, created_at, updated_at, last_login_at, metadata,
                    org_id, org_role, onboarding_completed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, '{}', ?, ?, 0)
                """,
                (
                    firebase_uid,
                    email,
                    name,
                    role,
                    case_manager_id,
                    provider,
                    decoded_token.get("picture") or "",
                    now,
                    now,
                    now,
                    org_id,
                    org_role,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
        return self._row_to_user(row)

    # ── First-login onboarding / org creation ──────────────────────────────
    #
    # All of these take a token-derived firebase_uid; the caller (router) never
    # passes a client-supplied role or org authority. Role/org_role are assigned
    # by the server: an org creator becomes its admin/owner; an invite-joiner
    # inherits the role recorded on the invite.

    def _generate_org_id(self) -> str:
        return "org_" + uuid.uuid4().hex[:12]

    def _assign_user_to_org(
        self,
        conn: sqlite3.Connection,
        firebase_uid: str,
        org_id: str,
        org_role: str,
        app_role: str,
    ) -> None:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            UPDATE user_profiles
            SET org_id = ?, org_role = ?, role = ?, onboarding_completed = 1,
                updated_at = ?
            WHERE firebase_uid = ?
            """,
            (org_id, org_role, app_role, now, firebase_uid),
        )

    def create_organization(
        self,
        firebase_uid: str,
        name: str,
        org_type: str,
    ) -> AuthenticatedUser:
        """Create an org and make the calling user its owner/admin.

        Role authority is server-assigned: the creator becomes app ``admin`` +
        ``org_admin`` of the new org. Raises HTTPException(400) on bad input.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Organization name is required")
        if len(clean_name) > 120:
            raise HTTPException(status_code=400, detail="Organization name is too long")
        clean_type = (org_type or "").strip().lower()
        if clean_type not in ALLOWED_ORG_TYPES:
            raise HTTPException(status_code=400, detail="Invalid organization type")

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT firebase_uid FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="User profile not found")

            org_id = self._generate_org_id()
            now_dt = datetime.utcnow()
            now = now_dt.isoformat()
            # New orgs start on the free trial (internal billing model only — no
            # Stripe customer/subscription is created; those columns stay NULL).
            trial_ends = (
                now_dt + timedelta(days=billing_plans.DEFAULT_TRIAL_DAYS)
            ).isoformat()
            conn.execute(
                """
                INSERT INTO organizations
                    (org_id, name, status, plan, org_type, created_by, created_at, updated_at,
                     billing_status, plan_code, trial_ends_at)
                VALUES (?, ?, 'active', NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    org_id, clean_name, clean_type, firebase_uid, now, now,
                    billing_plans.DEFAULT_BILLING_STATUS,
                    billing_plans.DEFAULT_PLAN_CODE,
                    trial_ends,
                ),
            )
            self._assign_user_to_org(conn, firebase_uid, org_id, ORG_ADMIN_ROLE, ADMIN_ROLE)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
        return self._row_to_user(row)

    def create_individual_workspace(self, firebase_uid: str) -> AuthenticatedUser:
        """Create a personal workspace org behind the scenes and assign owner."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT full_name, email FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User profile not found")
        label = (row["full_name"] or "").strip() or (row["email"] or "").split("@", 1)[0]
        workspace_name = f"{label}'s Workspace" if label else "Personal Workspace"
        return self.create_organization(firebase_uid, workspace_name, "individual")

    def accept_invite(self, firebase_uid: str, token: str) -> AuthenticatedUser:
        """Join an org via invite token. The org_role comes from the invite,
        never from the client. Raises HTTPException(400) when invalid/expired."""
        clean_token = (token or "").strip()
        if not clean_token:
            raise HTTPException(status_code=400, detail="Invite token is required")

        with self._connect() as conn:
            invite = conn.execute(
                "SELECT * FROM invites WHERE token = ?",
                (clean_token,),
            ).fetchone()
            if not invite:
                raise HTTPException(status_code=400, detail="Invalid invite token")
            if (invite["status"] or "").strip().lower() != "pending":
                raise HTTPException(status_code=400, detail="This invite is no longer valid")
            expires_at = (invite["expires_at"] or "").strip()
            if expires_at:
                try:
                    if datetime.fromisoformat(expires_at) < datetime.utcnow():
                        raise HTTPException(status_code=400, detail="This invite has expired")
                except ValueError:
                    raise HTTPException(status_code=400, detail="This invite has expired")

            user_row = conn.execute(
                "SELECT firebase_uid FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail="User profile not found")

            org_role = (invite["org_role"] or ORG_MEMBER_ROLE).strip() or ORG_MEMBER_ROLE
            app_role = ADMIN_ROLE if org_role == ORG_ADMIN_ROLE else CASE_MANAGER_ROLE
            self._assign_user_to_org(conn, firebase_uid, invite["org_id"], org_role, app_role)
            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE invites SET status = 'accepted', accepted_at = ? WHERE invite_id = ?",
                (now, invite["invite_id"]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE firebase_uid = ?",
                (firebase_uid,),
            ).fetchone()
        return self._row_to_user(row)

    # ── Team management: invites + staff (org-admin only) ───────────────────
    #
    # Every method takes the caller's own org_id (resolved from the token by the
    # router via require_org_admin). org_id is never accepted from the client, so
    # an admin can only ever manage their own org's invites and staff.

    INVITE_TTL_DAYS = 14

    def _invite_to_dict(self, row: sqlite3.Row, *, include_token: bool = True) -> Dict[str, Any]:
        keys = row.keys()
        data = {
            "invite_id": row["invite_id"],
            "org_id": row["org_id"],
            "email": row["email"],
            "org_role": row["org_role"],
            "status": row["status"],
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
            "invited_by": row["invited_by"] if "invited_by" in keys else None,
            "invited_name": row["invited_name"] if "invited_name" in keys else None,
            "accepted_at": row["accepted_at"] if "accepted_at" in keys else None,
            "cancelled_at": row["cancelled_at"] if "cancelled_at" in keys else None,
        }
        if include_token:
            data["token"] = row["token"]
        return data

    def create_invite(
        self,
        org_id: str,
        email: str,
        org_role: str,
        *,
        invited_by: Optional[str] = None,
        invited_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_email = (email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            raise HTTPException(status_code=400, detail="A valid email address is required")
        role = (org_role or "").strip().lower()
        if role not in (ORG_ADMIN_ROLE, ORG_MEMBER_ROLE):
            raise HTTPException(status_code=400, detail="Invalid role")

        invite_id = "inv_" + uuid.uuid4().hex[:12]
        token = secrets.token_urlsafe(32)  # unguessable
        now = datetime.utcnow()
        expires_at = (now + timedelta(days=self.INVITE_TTL_DAYS)).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO invites
                    (invite_id, org_id, email, org_role, token, status, expires_at,
                     created_at, invited_by, invited_name)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (invite_id, org_id, clean_email, role, token, expires_at,
                 now.isoformat(), invited_by, (invited_name or "").strip() or None),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM invites WHERE invite_id = ?", (invite_id,)).fetchone()
        return self._invite_to_dict(row)

    def list_invites(self, org_id: str, *, pending_only: bool = True) -> list:
        with self._connect() as conn:
            if pending_only:
                rows = conn.execute(
                    "SELECT * FROM invites WHERE org_id = ? AND status = 'pending' ORDER BY created_at DESC",
                    (org_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM invites WHERE org_id = ? ORDER BY created_at DESC",
                    (org_id,),
                ).fetchall()
        return [self._invite_to_dict(r) for r in rows]

    def _owned_invite(self, conn: sqlite3.Connection, org_id: str, invite_id: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM invites WHERE invite_id = ? AND org_id = ?",
            (invite_id, org_id),
        ).fetchone()
        if not row:
            # 404 also covers cross-org access (don't reveal another org's invite).
            raise HTTPException(status_code=404, detail="Invite not found")
        return row

    def resend_invite(self, org_id: str, invite_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = self._owned_invite(conn, org_id, invite_id)
            if (row["status"] or "").lower() not in ("pending", "expired"):
                raise HTTPException(status_code=400, detail="Only pending invites can be resent")
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(days=self.INVITE_TTL_DAYS)).isoformat()
            conn.execute(
                "UPDATE invites SET token = ?, expires_at = ?, status = 'pending', cancelled_at = NULL WHERE invite_id = ?",
                (token, expires_at, invite_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM invites WHERE invite_id = ?", (invite_id,)).fetchone()
        return self._invite_to_dict(row)

    def cancel_invite(self, org_id: str, invite_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            self._owned_invite(conn, org_id, invite_id)
            conn.execute(
                "UPDATE invites SET status = 'cancelled', cancelled_at = ? WHERE invite_id = ?",
                (datetime.utcnow().isoformat(), invite_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM invites WHERE invite_id = ?", (invite_id,)).fetchone()
        return self._invite_to_dict(row, include_token=False)

    def list_staff(self, org_id: str) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT firebase_uid, email, full_name, role, org_role, case_manager_id, is_active
                FROM user_profiles WHERE org_id = ? ORDER BY full_name
                """,
                (org_id,),
            ).fetchall()
        return [
            {
                "firebase_uid": r["firebase_uid"],
                "email": r["email"],
                "full_name": r["full_name"],
                "role": r["role"],
                "org_role": r["org_role"],
                "case_manager_id": r["case_manager_id"],
                "is_active": bool(r["is_active"]),
                "status": "active" if r["is_active"] else "disabled",
            }
            for r in rows
        ]

    def _count_active_org_admins(self, conn: sqlite3.Connection, org_id: str) -> int:
        return conn.execute(
            "SELECT COUNT(*) FROM user_profiles WHERE org_id = ? AND org_role = ? AND is_active = 1",
            (org_id, ORG_ADMIN_ROLE),
        ).fetchone()[0]

    def _staff_in_org(self, conn: sqlite3.Connection, org_id: str, target_uid: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE firebase_uid = ? AND org_id = ?",
            (target_uid, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Staff member not found")
        return row

    def update_staff_role(self, org_id: str, target_uid: str, new_org_role: str) -> Dict[str, Any]:
        role = (new_org_role or "").strip().lower()
        if role not in (ORG_ADMIN_ROLE, ORG_MEMBER_ROLE):
            raise HTTPException(status_code=400, detail="Invalid role")
        with self._connect() as conn:
            target = self._staff_in_org(conn, org_id, target_uid)
            # Block demoting the last active org admin.
            if (target["org_role"] == ORG_ADMIN_ROLE and role != ORG_ADMIN_ROLE
                    and bool(target["is_active"]) and self._count_active_org_admins(conn, org_id) <= 1):
                raise HTTPException(status_code=400, detail="Cannot demote the last organization admin")
            app_role = ADMIN_ROLE if role == ORG_ADMIN_ROLE else CASE_MANAGER_ROLE
            conn.execute(
                "UPDATE user_profiles SET org_role = ?, role = ?, updated_at = ? WHERE firebase_uid = ? AND org_id = ?",
                (role, app_role, datetime.utcnow().isoformat(), target_uid, org_id),
            )
            conn.commit()
        return {"firebase_uid": target_uid, "org_role": role, "role": app_role}

    def disable_staff(self, org_id: str, target_uid: str) -> Dict[str, Any]:
        """Remove a staff member's access by deactivating their profile.

        A deactivated user fails resolve_request_user (403) on every guarded
        endpoint, so they can no longer reach org data."""
        with self._connect() as conn:
            target = self._staff_in_org(conn, org_id, target_uid)
            # Block removing the last active org admin (also covers an admin
            # removing themselves while they are the only admin).
            if (target["org_role"] == ORG_ADMIN_ROLE and bool(target["is_active"])
                    and self._count_active_org_admins(conn, org_id) <= 1):
                raise HTTPException(status_code=400, detail="Cannot remove the last organization admin")
            conn.execute(
                "UPDATE user_profiles SET is_active = 0, updated_at = ? WHERE firebase_uid = ? AND org_id = ?",
                (datetime.utcnow().isoformat(), target_uid, org_id),
            )
            conn.commit()
        return {"firebase_uid": target_uid, "is_active": False, "status": "disabled"}

    # ── Platform super-admin (owner command center) ─────────────────────────
    #
    # Super-admin is an email allowlist, deliberately separate from org/app admin
    # roles, so a normal org admin is never a platform super-admin and cannot
    # elevate by sending role/org claims.

    def super_admin_emails(self) -> set:
        emails = {
            item.strip().lower()
            for item in (os.getenv("PLATFORM_SUPER_ADMIN_EMAILS") or "").split(",")
            if item.strip()
        }
        emails.update(PLATFORM_SUPER_ADMIN_EMAILS)
        return emails

    def is_platform_super_admin(self, user: AuthenticatedUser) -> bool:
        return bool(user) and (user.email or "").strip().lower() in self.super_admin_emails()

    def is_org_suspended(self, org_id: Optional[str]) -> bool:
        """True only when an org is explicitly suspended. The default/internal org
        is never treated as suspended (defense against lockout). Fails open."""
        org = (org_id or "").strip()
        if not org or org == DEFAULT_ORG_ID:
            return False
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT status FROM organizations WHERE org_id = ?", (org,)
                ).fetchone()
        except Exception:
            return False
        return bool(row) and (row["status"] or "").strip().lower() == "suspended"

    def platform_overview(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total_orgs = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
            total_users = conn.execute("SELECT COUNT(*) FROM user_profiles").fetchone()[0]
            active_users = conn.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE is_active = 1"
            ).fetchone()[0]
        return {"total_orgs": total_orgs, "total_users": total_users, "active_users": active_users}

    def list_organizations(self) -> list:
        with self._connect() as conn:
            orgs = conn.execute(
                """
                SELECT org_id, name, org_type, status, created_at, created_by
                FROM organizations ORDER BY created_at DESC
                """
            ).fetchall()
            counts = conn.execute(
                "SELECT org_id, COUNT(*) total, SUM(is_active) active FROM user_profiles GROUP BY org_id"
            ).fetchall()
        by_org = {c["org_id"]: c for c in counts}
        result = []
        for o in orgs:
            c = by_org.get(o["org_id"])
            result.append({
                "org_id": o["org_id"],
                "name": o["name"],
                "org_type": o["org_type"],
                "status": o["status"] or "active",
                "created_at": o["created_at"],
                "created_by": o["created_by"],
                "user_count": (c["total"] if c else 0),
                "active_user_count": (int(c["active"]) if c and c["active"] is not None else 0),
            })
        return result

    def get_organization_detail(self, org_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            org = conn.execute(
                """
                SELECT org_id, name, org_type, status, plan, created_at, created_by, updated_at
                FROM organizations WHERE org_id = ?
                """,
                (org_id,),
            ).fetchone()
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            pending_invites = conn.execute(
                "SELECT COUNT(*) FROM invites WHERE org_id = ? AND status = 'pending'", (org_id,)
            ).fetchone()[0]
        return {
            "organization": {
                "org_id": org["org_id"],
                "name": org["name"],
                "org_type": org["org_type"],
                "status": org["status"] or "active",
                "created_at": org["created_at"],
                "created_by": org["created_by"],
                "updated_at": org["updated_at"],
                # Subscription is a placeholder until billing exists — never PHI/secret.
                "subscription": {"plan": org["plan"], "status": "not_configured"},
            },
            "staff": self.list_staff(org_id),  # staff metadata only (no client/PHI data)
            "pending_invites": pending_invites,
        }

    def search_users(self, query: str, *, limit: int = 50) -> list:
        q = (query or "").strip()
        with self._connect() as conn:
            if q:
                like = f"%{q.lower()}%"
                rows = conn.execute(
                    """
                    SELECT email, full_name, role, org_id, org_role, is_active, case_manager_id
                    FROM user_profiles
                    WHERE LOWER(email) LIKE ? OR LOWER(full_name) LIKE ?
                    ORDER BY email LIMIT ?
                    """,
                    (like, like, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT email, full_name, role, org_id, org_role, is_active, case_manager_id
                    FROM user_profiles ORDER BY email LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "email": r["email"],
                "full_name": r["full_name"],
                "role": r["role"],
                "org_id": r["org_id"],
                "org_role": r["org_role"],
                "is_active": bool(r["is_active"]),
                "case_manager_id": r["case_manager_id"],
            }
            for r in rows
        ]

    def set_org_status(self, org_id: str, status: str, *, confirm: bool = False) -> Dict[str, Any]:
        new_status = (status or "").strip().lower()
        if new_status not in ("active", "suspended"):
            raise HTTPException(status_code=400, detail="Invalid status")
        # Guard the default/internal org against accidental suspension.
        if org_id == DEFAULT_ORG_ID and new_status == "suspended" and not confirm:
            raise HTTPException(
                status_code=400,
                detail="Refusing to suspend the default organization without explicit confirmation",
            )
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM organizations WHERE org_id = ?", (org_id,)
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Organization not found")
            conn.execute(
                "UPDATE organizations SET status = ?, updated_at = ? WHERE org_id = ?",
                (new_status, datetime.utcnow().isoformat(), org_id),
            )
            conn.commit()
        logger.info("SUPER-ADMIN: org %s status set to %s", org_id, new_status)
        return {"org_id": org_id, "status": new_status}

    # ── Billing + plan limits (internal model; Stripe-disabled) ─────────────
    #
    # Reads are org-scoped by the caller (the router passes the token-derived
    # org_id, never a client-supplied one). The manual setter is reachable only
    # from the super-admin router. No method here makes a Stripe call or touches
    # the stripe_* placeholder columns.

    def count_active_staff(self, org_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE org_id = ? AND is_active = 1",
                (org_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def get_org_billing(self, org_id: str) -> Dict[str, Any]:
        """Raw billing fields for an org, with defaults applied for any unset
        column. Never raises for a missing org — returns trial defaults so the
        UI degrades gracefully rather than 500-ing."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT billing_status, plan_code, trial_ends_at, subscription_provider,
                       stripe_customer_id, stripe_subscription_id
                FROM organizations WHERE org_id = ?
                """,
                (org_id,),
            ).fetchone()
        if not row:
            return {
                "billing_status": billing_plans.DEFAULT_BILLING_STATUS,
                "plan_code": billing_plans.DEFAULT_PLAN_CODE,
                "trial_ends_at": None,
                "subscription_provider": None,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
            }
        return {
            "billing_status": (row["billing_status"] or billing_plans.DEFAULT_BILLING_STATUS),
            "plan_code": (row["plan_code"] or billing_plans.DEFAULT_PLAN_CODE),
            "trial_ends_at": row["trial_ends_at"],
            "subscription_provider": row["subscription_provider"],
            # stripe_* are inert placeholders — surfaced as booleans only so no
            # opaque IDs leak, and never as live billing identifiers.
            "stripe_customer_id": row["stripe_customer_id"],
            "stripe_subscription_id": row["stripe_subscription_id"],
        }

    def set_org_billing(
        self,
        org_id: str,
        *,
        plan_code: Optional[str] = None,
        billing_status: Optional[str] = None,
        trial_ends_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manually set an org's plan/status (super-admin only, no Stripe).

        Used for comped/internal accounts and testing. Validates against the
        internal catalog/status list. Raises HTTPException(400/404) on bad input.
        """
        updates = []
        params: list = []
        if plan_code is not None:
            if not billing_plans.is_valid_plan_code(plan_code):
                raise HTTPException(status_code=400, detail="Invalid plan_code")
            updates.append("plan_code = ?")
            params.append(plan_code.strip().lower())
        if billing_status is not None:
            if not billing_plans.is_valid_billing_status(billing_status):
                raise HTTPException(status_code=400, detail="Invalid billing_status")
            updates.append("billing_status = ?")
            params.append(billing_status.strip().lower())
        if trial_ends_at is not None:
            # Accept empty string to clear the trial date; otherwise store as-is.
            updates.append("trial_ends_at = ?")
            params.append(trial_ends_at.strip() or None)
        if not updates:
            raise HTTPException(status_code=400, detail="No billing fields to update")

        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM organizations WHERE org_id = ?", (org_id,)
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Organization not found")
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(org_id)
            conn.execute(
                f"UPDATE organizations SET {', '.join(updates)} WHERE org_id = ?",
                tuple(params),
            )
            conn.commit()
        logger.info("SUPER-ADMIN: org %s billing updated (%s)", org_id, ", ".join(updates[:-1]))
        return self.get_org_billing(org_id)

    def resolve_request_user(self, request: Request) -> AuthenticatedUser:
        user = getattr(request.state, "auth_user", None)
        if not isinstance(user, AuthenticatedUser):
            raise HTTPException(status_code=401, detail="Authentication required")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is inactive")
        # Platform suspension: users in a suspended org lose guarded app access.
        if self.is_org_suspended(user.org_id):
            raise HTTPException(status_code=403, detail="Organization access is suspended")
        return user

    def is_test_auth_enabled(self) -> bool:
        if (os.getenv("ENABLE_TEST_AUTH") or "").strip().lower() not in TRUE_VALUES:
            return False

        environment_values = {
            (os.getenv("APP_ENV") or "").strip().lower(),
            (os.getenv("ENVIRONMENT") or "").strip().lower(),
            (os.getenv("RAILWAY_ENVIRONMENT") or "").strip().lower(),
        }
        if environment_values & PRODUCTION_ENVIRONMENTS:
            logger.error("ENABLE_TEST_AUTH ignored because a production environment is configured.")
            return False

        return bool(environment_values & TEST_AUTH_ENVIRONMENTS)

    def test_user_from_request(self, request: Request) -> AuthenticatedUser:
        role = (request.headers.get("X-Test-Auth-Role") or ADMIN_ROLE).strip().lower()
        if role not in ALLOWED_ROLES:
            role = ADMIN_ROLE
        case_manager_id = (
            request.headers.get("X-Test-Auth-Case-Manager-Id")
            or request.headers.get("X-Test-Auth-Case-Manager")
            or "cm_001"
        ).strip()
        firebase_uid = (
            request.headers.get("X-Test-Auth-Uid")
            or request.headers.get("X-Test-Auth-User")
            or "test-firebase-uid"
        ).strip()
        return AuthenticatedUser(
            firebase_uid=firebase_uid,
            email=(request.headers.get("X-Test-Auth-Email") or "case.manager@example.com").strip().lower(),
            full_name=(request.headers.get("X-Test-Auth-Name") or "Test Case Manager").strip(),
            role=role,
            case_manager_id=case_manager_id,
            auth_provider="test",
            is_active=True,
            org_id=DEFAULT_ORG_ID,
            org_role=ORG_ADMIN_ROLE,
        )

    def _row_to_user(self, row: sqlite3.Row) -> AuthenticatedUser:
        keys = row.keys()
        onboarding = bool(row["onboarding_completed"]) if "onboarding_completed" in keys else True
        return AuthenticatedUser(
            firebase_uid=row["firebase_uid"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            case_manager_id=row["case_manager_id"],
            auth_provider=row["auth_provider"],
            is_active=bool(row["is_active"]),
            org_id=(row["org_id"] or DEFAULT_ORG_ID),
            org_role=(row["org_role"] or ORG_MEMBER_ROLE),
            onboarding_completed=onboarding,
        )


auth_service = FirebaseAuthService()


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    return auth_service.resolve_request_user(request)


def require_user(request: Request) -> AuthenticatedUser:
    """Phase 2 guard: resolve the authenticated request user.

    Thin wrapper over the existing request-user resolution. It introduces no
    new auth system and does not change the global middleware — it simply gives
    route handlers an explicit guard call (and the hook where org/ownership
    enforcement attaches via assert_client_access).
    """
    return auth_service.resolve_request_user(request)


def require_org_admin(request: Request) -> AuthenticatedUser:
    """Phase 2 placeholder guard for future org-admin routes.

    Not wired to any UI/endpoint yet. Accepts either an org admin (org_role)
    or an existing platform admin (role) so it is safe to adopt later.
    """
    user = require_user(request)
    if user.org_role != ORG_ADMIN_ROLE and not user.is_admin:
        raise HTTPException(status_code=403, detail="Organization admin required")
    return user


def require_super_admin(request: Request) -> AuthenticatedUser:
    """Guard for the Super Admin Panel. Authenticates the request, then enforces
    the platform super-admin allowlist server-side (never from frontend claims)."""
    user = auth_service.resolve_request_user(request)
    if not auth_service.is_platform_super_admin(user):
        raise HTTPException(status_code=403, detail="Platform super admin required")
    return user


def require_role(user: AuthenticatedUser, allowed_roles: Iterable[str]) -> None:
    allowed = set(allowed_roles)
    if user.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
