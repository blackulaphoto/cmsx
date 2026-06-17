from __future__ import annotations

import json
import logging
import os
import sqlite3
import base64
from dataclasses import dataclass
from datetime import datetime
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
AUTH_DB_PATH = DB_DIR / "auth.db"
ADMIN_ROLE = "admin"
CASE_MANAGER_ROLE = "case_manager"
ALLOWED_ROLES = {ADMIN_ROLE, CASE_MANAGER_ROLE}
ORG_ADMIN_ROLE = "org_admin"
ORG_MEMBER_ROLE = "member"
BOOTSTRAP_ADMIN_EMAILS = {"blackulaphotography@gmail.com"}
TRUE_VALUES = {"1", "true", "yes", "on"}
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

            conn.commit()
            self._seed_default_org(conn)
            self._backfill_user_orgs(conn)
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
            conn.execute(
                """
                INSERT INTO user_profiles (
                    firebase_uid, email, full_name, role, case_manager_id, auth_provider,
                    photo_url, is_active, created_at, updated_at, last_login_at, metadata,
                    org_id, org_role
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, '{}', ?, ?)
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

    def resolve_request_user(self, request: Request) -> AuthenticatedUser:
        user = getattr(request.state, "auth_user", None)
        if not isinstance(user, AuthenticatedUser):
            raise HTTPException(status_code=401, detail="Authentication required")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is inactive")
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
        )


auth_service = FirebaseAuthService()


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    return auth_service.resolve_request_user(request)


def require_role(user: AuthenticatedUser, allowed_roles: Iterable[str]) -> None:
    allowed = set(allowed_roles)
    if user.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
