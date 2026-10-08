"""Translate backend rows into the optimizer's framework-free data contract."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from math import isfinite
from typing import Any, Iterable, Mapping

from database import get_db_connection


# Approximate village centres used for relative-distance ranking.
VILLAGE_COORDINATES: dict[str, tuple[float, float]] = {
    "kattankulathur": (12.8230, 80.0440),
    "potheri": (12.8214, 80.0397),
    "maraimalai nagar": (12.7930, 80.0250),
}

MACHINERY_TYPES = {"tractor", "rotavator", "harvester"}
SOLAR_TYPES = {"solar_pump"}
INPUT_TYPES = {"seed", "input", "compost", "mulch"}

DEFAULT_AVAILABILITY: dict[str, tuple[str, str]] = {
    "machinery": ("08:00", "18:00"),
    "solar": ("10:00", "16:00"),
}

_PACKAGED_INPUT = re.compile(
    r"^\s*(?P<label>.+?)\s*-\s*"
    r"(?P<quantity>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[A-Za-z]+)\s*$"
)


def _row_dict(row: Any, row_kind: str) -> dict[str, Any]:
    """Return a plain dict for dictionaries and sqlite3.Row-like objects."""

    if isinstance(row, Mapping):
        return dict(row)

    try:
        return dict(row)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{row_kind} row must be mapping-like"
        ) from exc


def _identifier(value: Any) -> str:
    return str(value).strip()


def _resource_type(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


def village_location(village: Any) -> dict[str, float]:
    """Return approximate coordinates for a supported village."""

    key = " ".join(
        str(village).strip().lower().split()
    )

    try:
        latitude, longitude = VILLAGE_COORDINATES[key]
    except KeyError as exc:
        supported = ", ".join(
            sorted(VILLAGE_COORDINATES)
        )

        raise ValueError(
            f"unknown village {village!r}; "
            f"supported villages: {supported}"
        ) from exc

    return {
        "latitude": latitude,
        "longitude": longitude,
    }


def _finite_number(
    value: Any,
    field_name: str,
) -> float:

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be numeric"
        )

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be numeric"
        ) from exc

    if not isfinite(number):
        raise ValueError(
            f"{field_name} must be finite"
        )

    return number


def _clean_number(
    value: float,
) -> int | float:

    return (
        int(value)
        if value.is_integer()
        else value
    )


def _available(value: Any) -> bool:

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "available",
        }

    return value == 1 or value is True


def _input_details(
    name: Any,
    total_price: Any,
) -> dict[str, Any]:

    match = _PACKAGED_INPUT.match(
        str(name)
    )

    if not match:
        raise ValueError(
            f"input name {name!r} must use "
            "'<item> - <quantity> <unit>' format"
        )

    label = _resource_type(
        match.group("label")
    )

    if label.endswith("_seeds"):
        label = f"{label[:-6]}_seed"

    quantity = _finite_number(
        match.group("quantity"),
        "quantity",
    )

    if quantity <= 0:
        raise ValueError(
            "quantity must be greater than zero"
        )

    price = _finite_number(
        total_price,
        "total_price",
    )

    if price < 0:
        raise ValueError(
            "total_price cannot be negative"
        )

    return {
        "subtype": label,
        "quantity": _clean_number(quantity),
        "unit": match.group("unit").lower(),
        "price_per_unit": price / quantity,
    }


def _owner_names(
    farmers: Iterable[Any],
) -> dict[str, str]:

    names: dict[str, str] = {}

    for raw_farmer in farmers:
        farmer = _row_dict(
            raw_farmer,
            "farmer",
        )

        if (
            farmer.get("id") is not None
            and farmer.get("name") is not None
        ):
            names[
                _identifier(farmer["id"])
            ] = str(farmer["name"])

    return names


def _clock_after(
    start: str,
    hours: Any,
) -> str:

    parsed = datetime.strptime(
        start,
        "%H:%M",
    )

    duration = _finite_number(
        hours,
        "booking hours",
    )

    if duration <= 0:
        raise ValueError(
            "booking hours must be greater than zero"
        )

    return (
        parsed + timedelta(hours=duration)
    ).strftime("%H:%M")


def _adapt_booking(
    raw_booking: Any,
    default_start: str,
) -> dict[str, Any] | None:

    booking = _row_dict(
        raw_booking,
        "booking",
    )

    start = (
        booking.get("start")
        or booking.get("start_time")
        or default_start
    )

    end = (
        booking.get("end")
        or booking.get("end_time")
    )

    if end is None:
        try:
            end = _clock_after(
                str(start),
                booking.get("hours", 1),
            )
        except ValueError:
            return None

    return {
        "date": booking.get(
            "booking_date",
            booking.get("date"),
        ),
        "start": str(start),
        "end": str(end),
        "status": booking.get(
            "status",
            "confirmed",
        ),
    }


def normalize_resource(
    resource: Any,
    farmers: Iterable[Any],
    bookings: Iterable[Any] = (),
) -> dict[str, Any]:
    """Normalize one backend resource row for optimizer.create_plan."""

    row = _row_dict(
        resource,
        "resource",
    )

    resource_type = _resource_type(
        row.get(
            "resource_type",
            row.get("type", ""),
        )
    )

    if not resource_type:
        raise ValueError(
            "resource_type is required"
        )

    owner_id = row.get("owner_id")
    owner_name = row.get("owner_name")

    if (
        owner_name is None
        and owner_id is not None
    ):
        owner_name = _owner_names(
            farmers
        ).get(
            _identifier(owner_id)
        )

    if owner_name is None:
        owner_name = "Unknown"

    if (
        row.get("latitude") is not None
        and row.get("longitude") is not None
    ):
        location = {
            "latitude": _finite_number(
                row["latitude"],
                "latitude",
            ),
            "longitude": _finite_number(
                row["longitude"],
                "longitude",
            ),
        }
    else:
        location = village_location(
            row.get("village")
        )

    normalized: dict[str, Any] = {
        "id": row.get("id"),
        "name": str(
            row.get(
                "name",
                resource_type.replace(
                    "_",
                    " ",
                ).title(),
            )
        ),
        "type": resource_type,
        "owner_name": str(owner_name),
        "status": (
            "available"
            if _available(
                row.get("available", 1)
            )
            else "unavailable"
        ),
        **location,
    }

    if resource_type in MACHINERY_TYPES:

        normalized["price_per_hour"] = (
            row.get("price_per_hour")
        )

        default_start, default_end = (
            DEFAULT_AVAILABILITY[
                "machinery"
            ]
        )

        normalized["available_from"] = (
            row.get(
                "available_from",
                default_start,
            )
        )

        normalized["available_until"] = (
            row.get(
                "available_until",
                default_end,
            )
        )

    elif resource_type in SOLAR_TYPES:

        normalized["price_per_hour"] = (
            row.get("price_per_hour")
        )

        default_start, default_end = (
            DEFAULT_AVAILABILITY[
                "solar"
            ]
        )

        normalized["available_from"] = (
            row.get(
                "available_from",
                default_start,
            )
        )

        normalized["available_until"] = (
            row.get(
                "available_until",
                default_end,
            )
        )

    elif resource_type in INPUT_TYPES:

        total_price = row.get(
            "total_price",
            row.get("price_per_hour"),
        )

        normalized.update(
            _input_details(
                row.get("name"),
                total_price,
            )
        )

        if resource_type not in {
            "seed",
            "input",
        }:
            normalized["type"] = "input"

    default_booking_start = str(
        normalized.get(
            "available_from",
            "08:00",
        )
    )

    resource_bookings: list[
        dict[str, Any]
    ] = []

    for raw_booking in bookings:

        booking = _row_dict(
            raw_booking,
            "booking",
        )

        if (
            _identifier(
                booking.get("resource_id")
            )
            != _identifier(row.get("id"))
        ):
            continue

        adapted = _adapt_booking(
            booking,
            default_booking_start,
        )

        if adapted is not None:
            resource_bookings.append(
                adapted
            )

    if resource_bookings:
        normalized["bookings"] = (
            resource_bookings
        )

    return normalized


def normalize_resources(
    resources: Iterable[Any],
    farmers: Iterable[Any],
    bookings: Iterable[Any] = (),
) -> list[dict[str, Any]]:
    """Normalize backend result rows."""

    farmer_rows = list(farmers)
    booking_rows = list(bookings)

    return [
        normalize_resource(
            resource,
            farmer_rows,
            booking_rows,
        )
        for resource in resources
    ]


def get_optimizer_resources() -> list[dict[str, Any]]:
    """
    Load resources from SQLite and convert them
    into the format expected by optimizer.py.
    """

    connection = get_db_connection()

    resources = connection.execute(
        """
        SELECT
            resources.*,
            farmers.name AS owner_name
        FROM resources
        LEFT JOIN farmers
            ON resources.owner_id = farmers.id
        """
    ).fetchall()

    farmers = connection.execute(
        "SELECT * FROM farmers"
    ).fetchall()

    bookings = connection.execute(
        "SELECT * FROM bookings"
    ).fetchall()

    connection.close()

    return normalize_resources(
        resources,
        farmers,
        bookings,
    )


__all__ = [
    "DEFAULT_AVAILABILITY",
    "VILLAGE_COORDINATES",
    "normalize_resource",
    "normalize_resources",
    "village_location",
    "get_optimizer_resources",
]