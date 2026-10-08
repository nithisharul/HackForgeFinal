"""Demonstrate a complete plan built from Shafaque's backend-shaped rows."""

from __future__ import annotations

import json

try:
    from .services.planner_service import build_plan_from_backend_data
except ImportError:  # Direct execution: python backend/demo_backend_plan.py
    from services.planner_service import build_plan_from_backend_data


REQUEST = {
    "farmer_id": 7,
    "plan_id": 201,
    "crop": "tomato",
    "area": 2,
    "date": "2026-09-09",
    "requirements": {
        "tractor": True,
        "solar_pump": True,
        "tomato_seed_kg": 10,
    },
}

FARMERS = [
    {"id": 1, "name": "Ravi Kumar", "village": "Kattankulathur"},
    {"id": 2, "name": "Priya Devi", "village": "Potheri"},
    {"id": 5, "name": "Suresh B", "village": "Potheri"},
    {"id": 7, "name": "Raju", "village": "Kattankulathur"},
]

RESOURCES = [
    {
        "id": 1,
        "name": "Mahindra Tractor",
        "resource_type": "tractor",
        "owner_id": 1,
        "village": "Kattankulathur",
        "price_per_hour": 450,
        "available": 1,
    },
    {
        "id": 5,
        "name": "Solar Pump 1",
        "resource_type": "solar_pump",
        "owner_id": 5,
        "village": "Potheri",
        "price_per_hour": 80,
        "available": 1,
    },
    {
        "id": 8,
        "name": "Tomato Seeds - 10 kg",
        "resource_type": "seed",
        "owner_id": 2,
        "village": "Potheri",
        "price_per_hour": 500,
        "available": 1,
    },
]


if __name__ == "__main__":
    plan = build_plan_from_backend_data(REQUEST, FARMERS, RESOURCES, bookings=[])
    print(json.dumps(plan, indent=2))
