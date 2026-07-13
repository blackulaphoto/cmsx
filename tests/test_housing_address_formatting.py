"""Tests for sober-living search result address formatting.

Regression coverage for a demo-facing bug: rows where the street `address`
field is stored equal to the city (bad source data) and `zipCode` is NULL
rendered as "Los Angeles, Los Angeles, CA None" in the UI.
"""

import sqlite3

import pytest

from backend.modules.housing.simple_housing_tools import (
    HousingResourceTools,
    _format_facility_address,
)


def _seed_treatment_centers(db_path, rows):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE treatment_centers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            address TEXT,
            city TEXT,
            zipCode TEXT,
            phone TEXT,
            website TEXT,
            servesPopulation TEXT,
            acceptsMediCal INTEGER,
            acceptsMedicare INTEGER,
            acceptsPrivateInsurance INTEGER,
            priceRange TEXT,
            description TEXT,
            servicesOffered TEXT,
            amenities TEXT,
            isPublished INTEGER
        )
        """
    )
    for row in rows:
        conn.execute(
            """INSERT INTO treatment_centers
               (name, type, address, city, zipCode, phone, website, servesPopulation,
                acceptsMediCal, acceptsMedicare, acceptsPrivateInsurance, priceRange,
                description, servicesOffered, amenities, isPublished)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row.get("name", "Test Home"),
                "sober_living",
                row.get("address"),
                row.get("city"),
                row.get("zipCode"),
                row.get("phone", "555-000-0000"),
                row.get("website", ""),
                row.get("servesPopulation", "men"),
                row.get("acceptsMediCal", 0),
                row.get("acceptsMedicare", 0),
                row.get("acceptsPrivateInsurance", 0),
                row.get("priceRange", ""),
                row.get("description", ""),
                row.get("servicesOffered", ""),
                row.get("amenities", ""),
                1,
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def housing_tools(tmp_path):
    db_path = tmp_path / "virgil_st_test.db"
    yield db_path


def test_address_omits_null_zip_as_literal_none(housing_tools):
    _seed_treatment_centers(
        housing_tools, [{"name": "3B Housing", "address": "Los Angeles", "city": "Los Angeles", "zipCode": None}]
    )
    tools = HousingResourceTools(db_path=str(housing_tools))
    result = tools.search_sober_living()
    assert result["success"] is True
    address = result["results"][0]["address"]
    assert "None" not in address


def test_address_does_not_duplicate_city(housing_tools):
    _seed_treatment_centers(
        housing_tools, [{"name": "3B Housing", "address": "Los Angeles", "city": "Los Angeles", "zipCode": None}]
    )
    tools = HousingResourceTools(db_path=str(housing_tools))
    result = tools.search_sober_living()
    address = result["results"][0]["address"]
    assert address == "Los Angeles, CA"
    assert address.count("Los Angeles") == 1


def test_address_keeps_street_city_and_zip_for_well_formed_rows(housing_tools):
    _seed_treatment_centers(
        housing_tools,
        [{"name": "Full Address Home", "address": "123 Main St", "city": "Los Angeles", "zipCode": "90012"}],
    )
    tools = HousingResourceTools(db_path=str(housing_tools))
    result = tools.search_sober_living()
    address = result["results"][0]["address"]
    assert address == "123 Main St, Los Angeles, CA 90012"


class TestFormatFacilityAddressUnit:
    def test_none_zip_and_duplicate_street(self):
        assert _format_facility_address("Los Angeles", "Los Angeles", None) == "Los Angeles, CA"

    def test_well_formed(self):
        assert _format_facility_address("123 Main St", "Los Angeles", "90012") == "123 Main St, Los Angeles, CA 90012"

    def test_missing_street_and_zip(self):
        assert _format_facility_address("", "Los Angeles", "") == "Los Angeles, CA"

    def test_all_missing_never_prints_none(self):
        assert "None" not in _format_facility_address(None, None, None)
