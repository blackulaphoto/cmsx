from backend.auth.service import AuthenticatedUser


def make_test_user(
    *,
    firebase_uid: str = "uid-1",
    email: str = "case.manager@example.com",
    full_name: str = "Case Manager",
    role: str = "admin",
    case_manager_id: str = "cm_001",
) -> AuthenticatedUser:
    return AuthenticatedUser(
        firebase_uid=firebase_uid,
        email=email,
        full_name=full_name,
        role=role,
        case_manager_id=case_manager_id,
        auth_provider="test",
        is_active=True,
    )


def add_test_auth_middleware(app, user: AuthenticatedUser | None = None) -> None:
    auth_user = user or make_test_user()

    @app.middleware("http")
    async def inject_auth_user(request, call_next):
        request.state.auth_user = auth_user
        return await call_next(request)
