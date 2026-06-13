from backend.modules.admissions.profile import (
    PROFILE_META_KEY,
    apply_profile_defaults,
    build_shared_profile,
    build_shared_profile_from_client,
    extract_profile_updates,
    merge_shared_profile,
)


def test_build_shared_profile_normalizes_name_and_age():
    profile = build_shared_profile(
        {
            "first_name": "  Jane ",
            "last_name": " Doe  ",
            "date_of_birth": "2000-06-12",
            "zip_code": "90012",
            "program_type": "Residential",
            "intake_date": "2026-06-01",
        }
    )

    assert profile["full_name"] == "Jane Doe"
    assert profile["zip"] == "90012"
    assert profile["program"] == "Residential"
    assert profile["admission_date"] == "2026-06-01"
    assert isinstance(profile["age"], int)


def test_build_shared_profile_from_client_uses_client_shape():
    profile = build_shared_profile_from_client(
        {
            "first_name": "John",
            "last_name": "Smith",
            "zip_code": "90021",
            "program_type": "PHP",
            "intake_date": "2026-06-10",
        }
    )

    assert profile["full_name"] == "John Smith"
    assert profile["zip"] == "90021"
    assert profile["program"] == "PHP"
    assert profile["admission_date"] == "2026-06-10"


def test_extract_profile_updates_maps_repeated_fields():
    updates = extract_profile_updates(
        "client_face_sheet",
        {
            "legal_first_name": "Alicia",
            "legal_last_name": "Keys",
            "date_of_birth": "1990-01-02",
            "phone_mobile": "555-222-1111",
            "email": "alicia@example.com",
            "address_line1": "123 Main St",
            "city": "Los Angeles",
            "state": "CA",
            "zip": "90001",
            "emergency_contact_name": "Maria",
            "primary_payer_type": "Medi-Cal",
            "primary_member_id": "ABC123",
        },
    )

    assert updates["first_name"] == "Alicia"
    assert updates["last_name"] == "Keys"
    assert updates["full_name"] == "Alicia Keys"
    assert updates["phone"] == "555-222-1111"
    assert updates["insurance_provider"] == "Medi-Cal"
    assert updates["insurance_member_id"] == "ABC123"


def test_merge_shared_profile_keeps_existing_values_when_updates_blank():
    merged = merge_shared_profile(
        {"first_name": "Alicia", "insurance_provider": "Medi-Cal"},
        {"first_name": "", "insurance_provider": None, "city": "Long Beach"},
    )

    assert merged["first_name"] == "Alicia"
    assert merged["insurance_provider"] == "Medi-Cal"
    assert merged["city"] == "Long Beach"


def test_apply_profile_defaults_fills_matching_fields_without_overwriting_touched_values():
    response = {
        "client_name": "Manual Alias",
        PROFILE_META_KEY: {
            "touched_fields": {
                "client_name": True,
                "phone_mobile": True,
            }
        },
    }
    shared_profile = {
        "first_name": "Alice",
        "last_name": "Walker",
        "full_name": "Alice Walker",
        "phone": "555-111-0000",
        "date_of_birth": "1988-03-01",
        "admission_date": "2026-06-12",
    }

    applied = apply_profile_defaults(response, shared_profile)

    assert applied["client_name"] == "Manual Alias"
    assert "phone_mobile" not in applied
    assert applied["date_of_birth"] == "1988-03-01"
    assert applied["assessment_date"] == "2026-06-12"
    assert applied[PROFILE_META_KEY]["touched_fields"]["client_name"] is True
