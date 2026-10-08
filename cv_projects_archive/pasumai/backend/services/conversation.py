"""Simple conversation state for KisanPool AI."""

from __future__ import annotations

from typing import Any


def merge_requests(
    current: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """Merge newly provided information into an existing request."""

    merged = current.copy()

    # Only update farmer ID when explicitly available.
    if new.get("farmer_id") is not None:
        merged["farmer_id"] = new["farmer_id"]

    # Only update crop and area when the new message provides them.
    if new.get("crop") is not None:
        merged["crop"] = new["crop"]

    if new.get("area") is not None:
        merged["area"] = new["area"]

    # Merge resource requirements.
    #
    # The parser currently puts False for resources that were NOT
    # mentioned. Therefore, only True values should overwrite
    # existing values during a conversation.
    current_requirements = merged.get("requirements", {}).copy()
    new_requirements = new.get("requirements", {})

    for key, value in new_requirements.items():
        if value is True:
            current_requirements[key] = True

        elif key.endswith("_seed_kg") and value is not None:
            current_requirements[key] = value

    merged["requirements"] = current_requirements

    return merged