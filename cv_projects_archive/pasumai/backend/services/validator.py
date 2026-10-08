"""Validation layer for parsed KisanPool AI requests."""

from __future__ import annotations

from typing import Any


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    """Check whether a parsed request contains enough information to optimize."""

    missing: list[str] = []

    # --------------------------------------------------
    # Crop
    # --------------------------------------------------

    if not request.get("crop"):
        missing.append("crop")

    # --------------------------------------------------
    # Farm area
    # --------------------------------------------------

    if request.get("area") is None:
        missing.append("area")

    # --------------------------------------------------
    # Resource requirement
    # --------------------------------------------------

    requirements = request.get("requirements", {})

    # Tractor or solar pump requested
    resource_requested = any(
        value is True
        for key, value in requirements.items()
        if key in {"tractor", "solar_pump"}
    )

    # Seed requirement also counts as a resource request
    seed_requested = any(
        key.endswith("_seed_kg") and value is not None
        for key, value in requirements.items()
    )

    if not resource_requested and not seed_requested:
        missing.append("resource")

    # --------------------------------------------------
    # Validation result
    # --------------------------------------------------

    return {
        "valid": len(missing) == 0,
        "missing": missing,
    }


def get_missing_questions(
    validation: dict[str, Any],
) -> list[str]:
    """Convert missing fields into clear questions for the farmer."""

    missing = validation.get("missing", [])
    questions: list[str] = []

    # --------------------------------------------------
    # Crop + area
    # --------------------------------------------------

    if "crop" in missing and "area" in missing:
        questions.append(
            "What crop are you growing, and how many acres is your farm?"
        )

    elif "crop" in missing:
        questions.append(
            "What crop are you growing?"
        )

    elif "area" in missing:
        questions.append(
            "How many acres is your farm?"
        )

    # --------------------------------------------------
    # Resource
    # --------------------------------------------------

    if "resource" in missing:
        questions.append(
            "What do you need help arranging, such as a tractor, "
            "irrigation, or seeds?"
        )

    return questions