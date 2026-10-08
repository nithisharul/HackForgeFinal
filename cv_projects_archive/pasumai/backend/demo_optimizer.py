"""Run the golden Raju scenario without a web server or database."""

from __future__ import annotations

import json

try:
    from .services.optimizer import create_plan
except ImportError:  # Direct execution: python backend/demo_optimizer.py
    from services.optimizer import create_plan


RAJU_REQUEST = {
    "farmer_id": 1,
    "crop": "tomato",
    "area": 2,
    "date": "2026-09-09",
    "requirements": {
        "tractor": True,
        "solar_pump": True,
        "tomato_seed_kg": 10,
    },
}

RAJU_LOCATION = {"latitude": 12.820, "longitude": 80.040}

SAMPLE_RESOURCES = [
    {
        "id": 3,
        "owner_id": 4,
        "owner_name": "Mani",
        "type": "tractor",
        "name": "Tractor #03",
        "price_per_hour": 450,
        "latitude": 12.823,
        "longitude": 80.044,
        "available_from": "09:00",
        "available_until": "16:00",
        "status": "available",
    },
    {
        "id": 4,
        "owner_id": 5,
        "owner_name": "Selvan",
        "type": "tractor",
        "name": "Tractor #04",
        "price_per_hour": 350,
        "latitude": 12.940,
        "longitude": 80.160,
        "available_from": "08:00",
        "available_until": "14:00",
        "status": "available",
    },
    {
        "id": 8,
        "owner_id": 7,
        "owner_name": "Community Pool",
        "type": "solar_pump",
        "name": "Solar Pump #02",
        "price_per_hour": 80,
        "latitude": 12.826,
        "longitude": 80.048,
        "available_from": "10:00",
        "available_until": "16:00",
        "status": "available",
    },
    {
        "id": 11,
        "owner_id": 8,
        "owner_name": "Arun",
        "type": "seed",
        "subtype": "tomato_seed",
        "quantity": 6,
        "unit": "kg",
        "price_per_unit": 30,
        "latitude": 12.821,
        "longitude": 80.041,
        "status": "available",
    },
    {
        "id": 14,
        "owner_id": 9,
        "owner_name": "Kumar",
        "type": "seed",
        "subtype": "tomato_seed",
        "quantity": 7,
        "unit": "kg",
        "price_per_unit": 35,
        "latitude": 12.828,
        "longitude": 80.046,
        "status": "available",
    },
    {
        "id": 15,
        "owner_id": 10,
        "owner_name": "Priya",
        "type": "seed",
        "subtype": "tomato_seed",
        "quantity": 3,
        "unit": "kg",
        "price_per_unit": 25,
        "latitude": 12.890,
        "longitude": 80.080,
        "status": "available",
    },
]


if __name__ == "__main__":
    print(json.dumps(create_plan(RAJU_REQUEST, SAMPLE_RESOURCES, RAJU_LOCATION), indent=2))
