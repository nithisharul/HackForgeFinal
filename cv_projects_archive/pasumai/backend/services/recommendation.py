"""AI recommendation and explanation layer for KisanPool AI."""

from __future__ import annotations

from typing import Any


def generate_recommendation(plan: dict[str, Any]) -> dict[str, Any]:
    """Generate a farmer-friendly explanation from an optimized plan."""

    recommendations: list[str] = []

    machinery = plan.get("machinery", {})
    irrigation = plan.get("irrigation", {})
    inputs = plan.get("inputs", [])
    impact = plan.get("impact", {})

    # Machinery recommendation
    if machinery.get("status") != "unavailable":
        name = machinery.get("name", "the selected machine")
        owner = machinery.get("owner", "the provider")
        cost = machinery.get("cost", 0)
        distance = machinery.get("distance_km", 0)

        recommendations.append(
            f"Use {name} from {owner}. "
            f"It was selected based on cost, distance, and availability. "
            f"Estimated machinery cost is Rs. {cost} and the resource is "
            f"{distance} km from the farm."
        )
    else:
        recommendations.append(
            "No suitable machinery is currently available for this request."
        )

    # Irrigation recommendation
    if irrigation.get("status") != "not_requested":
        if irrigation.get("status") != "unavailable":
            recommendations.append(
                f"Use {irrigation.get('name', 'the selected irrigation resource')} "
                f"from {irrigation.get('owner', 'the provider')} "
                f"from {irrigation.get('start')} to {irrigation.get('end')}."
            )
        else:
            recommendations.append(
                "Irrigation was requested, but no suitable pump is currently available."
            )

    # Resource pooling recommendation
    if inputs:
        owners = ", ".join(
            sorted({str(item.get("owner")) for item in inputs})
        )
        reused = impact.get("input_reused_kg", 0)

        recommendations.append(
            f"Pool {reused} kg of inputs from nearby farmers "
            f"({owners}) instead of sourcing everything individually."
        )

    # Savings recommendation
    savings = impact.get("savings", 0)
    distance_saved = impact.get("distance_saved_km", 0)

    if savings > 0:
        recommendations.append(
            f"This optimized plan saves approximately Rs. {savings} "
            f"compared with the normal estimated cost."
        )

    if distance_saved > 0:
        recommendations.append(
            f"The plan also avoids approximately {distance_saved} km "
            f"of travel."
        )

    return {
        "summary": recommendations,
        "savings": savings,
        "distance_saved_km": distance_saved,
    }