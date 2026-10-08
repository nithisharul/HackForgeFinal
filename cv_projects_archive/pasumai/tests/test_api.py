from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    database_path = tmp_path / "kisanpool-test.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE farmers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            village TEXT NOT NULL,
            phone TEXT
        );
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            owner_id INTEGER,
            village TEXT NOT NULL,
            price_per_hour REAL DEFAULT 0,
            available INTEGER DEFAULT 1
        );
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY,
            farmer_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            hours REAL DEFAULT 1,
            total_cost REAL DEFAULT 0,
            status TEXT DEFAULT 'confirmed'
        );
        """
    )
    connection.executemany(
        "INSERT INTO farmers (id, name, village) VALUES (?, ?, ?)",
        [
            (1, "Raju", "Kattankulathur"),
            (2, "Priya Devi", "Potheri"),
            (3, "Suresh B", "Maraimalai Nagar"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO resources
            (id, name, resource_type, owner_id, village, price_per_hour, available)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Mahindra Tractor", "tractor", 2, "Potheri", 450, 1),
            (2, "Solar Pump 1", "solar_pump", 3, "Maraimalai Nagar", 80, 1),
            (3, "Tomato Seeds - 10 kg", "seed", 2, "Potheri", 500, 1),
        ],
    )
    connection.commit()
    connection.close()

    def test_connection():
        result = sqlite3.connect(database_path)
        result.row_factory = sqlite3.Row
        return result

    monkeypatch.setattr(main, "get_db_connection", test_connection)
    with TestClient(main.app) as client:
        yield client, database_path


def test_farmers_endpoint_returns_backend_rows(api_client) -> None:
    client, _ = api_client

    response = client.get("/farmers")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Raju"


def test_resources_endpoint_returns_backend_rows(api_client) -> None:
    client, _ = api_client

    response = client.get("/resources")

    assert response.status_code == 200
    assert response.json()[0]["resource_type"] == "tractor"


def test_plan_endpoint_returns_real_optimized_plan(api_client) -> None:
    client, _ = api_client
    payload = {
        "farmer_id": 1,
        "message": (
            "I need a tractor, irrigation and 10kg tomato seeds tomorrow "
            "for my 2 acre farm"
        ),
    }

    response = client.post("/plan", json=payload)

    assert response.status_code == 200
    plan = response.json()
    assert plan["parsed_request"] == {
        "crop": "tomato",
        "area": 2,
        "date": (date.today() + timedelta(days=1)).isoformat(),
    }
    assert plan["machinery"]["resource_id"] == 1
    assert plan["irrigation"]["resource_id"] == 2
    assert plan["inputs"] == [
        {
            "resource_id": 3,
            "owner": "Priya Devi",
            "item": "Tomato Seeds",
            "quantity": 10,
            "unit": "kg",
        }
    ]


def test_plan_endpoint_ignores_unavailable_resource(api_client) -> None:
    client, database_path = api_client
    connection = sqlite3.connect(database_path)
    connection.execute("UPDATE resources SET available = 0 WHERE id = 1")
    connection.commit()
    connection.close()

    response = client.post(
        "/plan",
        json={
            "farmer_id": 1,
            "message": "I need a tractor for my 2 acre tomato farm tomorrow",
        },
    )

    assert response.status_code == 200
    assert response.json()["machinery"]["status"] == "unavailable"
