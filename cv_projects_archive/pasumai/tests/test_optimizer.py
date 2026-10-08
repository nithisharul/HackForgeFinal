from __future__ import annotations

import json

import pytest

from backend.demo_optimizer import RAJU_LOCATION, RAJU_REQUEST, SAMPLE_RESOURCES
from backend.services.optimizer import (
    create_plan,
    distance_km,
    find_best_machine,
    find_best_solar_pump,
    find_input_suppliers,
)


def resources_of_type(resource_type: str) -> list[dict]:
    return [dict(resource) for resource in SAMPLE_RESOURCES if resource["type"] == resource_type]


def test_haversine_distance_uses_kilometres() -> None:
    # One degree of longitude at the equator is approximately 111.2 km.
    assert distance_km(0, 0, 0, 1) == pytest.approx(111.195, rel=0.001)


def test_golden_raju_scenario_is_complete_and_json_serializable() -> None:
    plan = create_plan(RAJU_REQUEST, SAMPLE_RESOURCES, RAJU_LOCATION)

    assert plan["plan_id"] == 101
    assert plan["parsed_request"] == {
        "crop": "tomato",
        "area": 2,
        "date": "2026-09-09",
    }
    assert plan["machinery"]["resource_id"] == 3
    assert plan["machinery"]["start"] == "09:00"
    assert plan["machinery"]["end"] == "11:30"
    assert set(plan["machinery"]) == {
        "resource_id",
        "name",
        "owner",
        "start",
        "end",
        "cost",
        "distance_km",
    }
    assert plan["irrigation"]["resource_id"] == 8
    assert plan["irrigation"]["start"] == "13:00"
    assert plan["irrigation"]["end"] == "14:30"
    assert set(plan["irrigation"]) == {
        "resource_id",
        "name",
        "owner",
        "start",
        "end",
        "cost",
        "distance_km",
    }
    assert sum(item["quantity"] for item in plan["inputs"]) == 10
    assert {item["owner"] for item in plan["inputs"]} == {"Arun", "Kumar"}
    assert "input_fulfillment" not in plan
    assert plan["impact"]["solar_hours"] == 1.5
    assert plan["impact"]["input_reused_kg"] == 10
    json.dumps(plan)


def test_closer_slightly_more_expensive_tractor_beats_cheapest_far_one() -> None:
    resources = [
        {
            "id": 1,
            "owner_name": "Far Away",
            "type": "tractor",
            "name": "Cheap Tractor",
            "price_per_hour": 400,
            "latitude": 13.000,
            "longitude": 80.200,
            "available_from": "09:00",
            "available_until": "16:00",
            "status": "available",
        },
        {
            "id": 2,
            "owner_name": "Nearby",
            "type": "tractor",
            "name": "Nearby Tractor",
            "price_per_hour": 425,
            "latitude": 12.821,
            "longitude": 80.041,
            "available_from": "09:00",
            "available_until": "16:00",
            "status": "available",
        },
    ]

    selected = find_best_machine(RAJU_REQUEST, resources, RAJU_LOCATION)

    assert selected["resource_id"] == 2
    assert selected["cost"] == 1062.5


def test_reserved_tractor_is_ignored() -> None:
    resources = resources_of_type("tractor")
    resources[0]["status"] = "reserved"

    selected = find_best_machine(RAJU_REQUEST, resources, RAJU_LOCATION)

    assert selected["resource_id"] == 4


def test_current_booking_blocks_requested_machine_window() -> None:
    request = {**RAJU_REQUEST, "machinery_start": "09:00"}
    resources = resources_of_type("tractor")
    resources[0]["bookings"] = [
        {
            "date": "2026-09-09",
            "start": "10:00",
            "end": "11:00",
            "status": "confirmed",
        }
    ]

    selected = find_best_machine(request, resources, RAJU_LOCATION)

    assert selected["resource_id"] == 4


def test_solar_pump_uses_valid_daytime_window() -> None:
    selected = find_best_solar_pump(
        RAJU_REQUEST, resources_of_type("solar_pump"), RAJU_LOCATION
    )

    assert selected["resource_id"] == 8
    assert selected["start"] == "13:00"
    assert selected["end"] == "14:30"


def test_seed_requirement_is_fulfilled_from_two_nearby_farmers() -> None:
    result = find_input_suppliers(
        RAJU_REQUEST, resources_of_type("seed"), RAJU_LOCATION
    )

    assert result["requested"] == 10
    assert result["fulfilled"] == 10
    assert result["unmet"] == 0
    assert [(supplier["owner"], supplier["quantity"]) for supplier in result["suppliers"]] == [
        ("Arun", 6),
        ("Kumar", 4),
    ]


def test_partial_seed_quantity_is_reported_without_crashing() -> None:
    resources = resources_of_type("seed")[:2]
    resources[0]["quantity"] = 5
    resources[1]["quantity"] = 4
    request = {
        **RAJU_REQUEST,
        "requirements": {**RAJU_REQUEST["requirements"], "tomato_seed_kg": 20},
    }

    result = find_input_suppliers(request, resources, RAJU_LOCATION)
    plan = create_plan(request, resources, RAJU_LOCATION)

    assert result["fulfilled"] == 9
    assert result["unmet"] == 11
    assert plan["input_fulfillment"] == [
        {
            "item": "Tomato Seeds",
            "requested": 20,
            "fulfilled": 9,
            "unmet": 11,
            "unit": "kg",
        }
    ]
    assert plan["machinery"]["status"] == "unavailable"
    assert plan["irrigation"]["status"] == "unavailable"


def test_no_tractor_available_returns_unavailable() -> None:
    selected = find_best_machine(
        RAJU_REQUEST, resources_of_type("solar_pump"), RAJU_LOCATION
    )

    assert selected["status"] == "unavailable"
    assert "tractor" in selected["reason"]


def test_no_solar_pump_available_returns_unavailable() -> None:
    selected = find_best_solar_pump(
        RAJU_REQUEST, resources_of_type("tractor"), RAJU_LOCATION
    )

    assert selected["status"] == "unavailable"
    assert "solar pump" in selected["reason"]


def test_malformed_resources_are_skipped() -> None:
    malformed = {
        "id": 99,
        "owner_name": "Broken",
        "type": "tractor",
        "price_per_hour": "not-a-number",
        "latitude": None,
        "longitude": None,
        "available_from": "bad-time",
        "available_until": "16:00",
        "status": "available",
    }

    selected = find_best_machine(
        RAJU_REQUEST, [malformed, *resources_of_type("tractor")], RAJU_LOCATION
    )

    assert selected["resource_id"] == 3
