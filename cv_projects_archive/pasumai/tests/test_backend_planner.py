from __future__ import annotations

import json

import pytest

from backend.demo_backend_plan import FARMERS, REQUEST, RESOURCES
from backend.services.planner_service import build_plan_from_backend_data
from backend.services.resource_adapter import normalize_resource


def test_tractor_normalization() -> None:
    tractor = normalize_resource(RESOURCES[0], FARMERS)

    assert tractor == {
        "id": 1,
        "name": "Mahindra Tractor",
        "type": "tractor",
        "owner_name": "Ravi Kumar",
        "status": "available",
        "latitude": 12.823,
        "longitude": 80.044,
        "price_per_hour": 450,
        "available_from": "08:00",
        "available_until": "18:00",
    }


def test_solar_pump_normalization() -> None:
    pump = normalize_resource(RESOURCES[1], FARMERS)

    assert pump["type"] == "solar_pump"
    assert pump["owner_name"] == "Suresh B"
    assert pump["price_per_hour"] == 80
    assert pump["available_from"] == "10:00"
    assert pump["available_until"] == "16:00"


def test_seed_quantity_and_unit_price_are_parsed() -> None:
    seed = normalize_resource(RESOURCES[2], FARMERS)

    assert seed["type"] == "seed"
    assert seed["subtype"] == "tomato_seed"
    assert seed["quantity"] == 10
    assert seed["unit"] == "kg"
    assert seed["price_per_unit"] == pytest.approx(50)


def test_unavailable_backend_resource_is_ignored() -> None:
    unavailable_nearby = {**RESOURCES[0], "id": 99, "price_per_hour": 1, "available": 0}
    farther_available = {
        **RESOURCES[0],
        "id": 100,
        "owner_id": 2,
        "village": "Potheri",
        "price_per_hour": 500,
    }
    request = {
        **REQUEST,
        "requirements": {"tractor": True},
    }

    plan = build_plan_from_backend_data(
        request, FARMERS, [unavailable_nearby, farther_available], []
    )

    assert plan["machinery"]["resource_id"] == 100


def test_full_golden_raju_backend_scenario_works() -> None:
    plan = build_plan_from_backend_data(REQUEST, FARMERS, RESOURCES, [])

    assert plan["plan_id"] == 201
    assert plan["parsed_request"] == {
        "crop": "tomato",
        "area": 2,
        "date": "2026-09-09",
    }
    assert plan["machinery"]["resource_id"] == 1
    assert plan["machinery"]["start"] == "09:00"
    assert plan["machinery"]["end"] == "11:30"
    assert plan["irrigation"]["resource_id"] == 5
    assert plan["irrigation"]["start"] == "13:00"
    assert plan["irrigation"]["end"] == "14:30"
    assert plan["inputs"] == [
        {
            "resource_id": 8,
            "owner": "Priya Devi",
            "item": "Tomato Seeds",
            "quantity": 10,
            "unit": "kg",
        }
    ]
    assert "input_fulfillment" not in plan
    assert plan["impact"]["input_reused_kg"] == 10
    json.dumps(plan)
