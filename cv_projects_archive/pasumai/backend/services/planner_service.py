"""Application service joining backend-shaped data to the pure optimizer."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .optimizer import create_plan
from .pipeline import process_message
from .resource_adapter import normalize_resources, village_location


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    try:
        return dict(row)
    except (TypeError, ValueError) as exc:
        raise ValueError("farmer row must be mapping-like") from exc


def _farmer_location(
    farmer_id: Any,
    farmer_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    requesting_farmer = next(
        (
            farmer
            for farmer in farmer_rows
            if str(farmer.get("id")) == str(farmer_id)
        ),
        None,
    )
    if requesting_farmer is None:
        raise ValueError(f"farmer {farmer_id!r} was not found")

    if (
        requesting_farmer.get("latitude") is not None
        and requesting_farmer.get("longitude") is not None
    ):
        return {
            "latitude": requesting_farmer["latitude"],
            "longitude": requesting_farmer["longitude"],
        }
    return village_location(requesting_farmer.get("village"))


def build_plan_from_backend_data(
    request: Mapping[str, Any],
    farmers: Iterable[Any],
    resources: Iterable[Any],
    bookings: Iterable[Any],
) -> dict[str, Any]:
    """Build a plan from plain backend rows, without accessing the database."""

    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    farmer_id = request.get("farmer_id")
    if farmer_id is None:
        raise ValueError("request.farmer_id is required")

    farmer_rows = [_row_dict(farmer) for farmer in farmers]
    farmer_location = _farmer_location(farmer_id, farmer_rows)

    normalized_resources = normalize_resources(
        resources,
        farmer_rows,
        bookings,
    )
    return create_plan(request, normalized_resources, farmer_location)


def build_plan_from_backend_message(
    message: str,
    farmer_id: int,
    farmers: Iterable[Any],
    resources: Iterable[Any],
    bookings: Iterable[Any],
) -> dict[str, Any]:
    """Run a natural-language request against backend-shaped result rows."""

    farmer_rows = [_row_dict(farmer) for farmer in farmers]
    farmer_location = _farmer_location(farmer_id, farmer_rows)
    normalized_resources = normalize_resources(resources, farmer_rows, bookings)
    result = process_message(
        message=message,
        farmer_id=farmer_id,
        resources=normalized_resources,
        farmer_location=farmer_location,
    )
    if result.get("status") != "optimized":
        questions = result.get("questions", [])
        detail = " ".join(str(question) for question in questions)
        raise ValueError(detail or "request does not contain enough information")
    return result["plan"]


def build_plan_from_database(
    farmer_id: int,
    message: str,
    connection: Any,
) -> dict[str, Any]:
    """Load current backend rows and return their optimized message plan."""

    farmers = connection.execute("SELECT * FROM farmers").fetchall()
    resources = connection.execute("SELECT * FROM resources").fetchall()
    bookings = connection.execute("SELECT * FROM bookings").fetchall()
    return build_plan_from_backend_message(
        message,
        farmer_id,
        farmers,
        resources,
        bookings,
    )


__all__ = [
    "build_plan_from_backend_data",
    "build_plan_from_backend_message",
    "build_plan_from_database",
]
