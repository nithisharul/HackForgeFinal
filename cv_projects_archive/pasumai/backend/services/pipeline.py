"""End-to-end KisanPool AI request pipeline."""

from __future__ import annotations

from email.mime import message
from email import message
from typing import Any
from urllib import request

from services.recommendation import generate_recommendation
from services.session import ConversationSession
from services.conversation import merge_requests
from services.optimizer import create_plan
from services.parser import parse_request
from services.validator import (
        get_missing_questions,
    validate_request,
)


def process_message(
    message: str,
    farmer_id: int,
    resources: list[dict[str, Any]],
    farmer_location: dict[str, float],
    session: ConversationSession | None = None,
    current_request: dict[str, Any] | None = None,
) -> dict[str, Any]:

    
    """Process a farmer message.

    Parses the message, merges it with any previous request,
    validates the combined request, and runs the optimizer
    when enough information is available.
    """

    if session is not None:
        current_request = session.get()

    new_request = parse_request(
        message,
        farmer_id=farmer_id,
    )

    print("========== PIPELINE DEBUG ==========")
    print("CURRENT REQUEST:", current_request)
    print("NEW REQUEST:", new_request)
    print("MESSAGE:", message)
    print("====================================")

    if current_request is not None:
        request = merge_requests(
            current_request,
            new_request,
        )
    else:
        request = new_request

    if session is not None:
        session.update(request)

    validation = validate_request(request)

    if not validation["valid"]:
        return {
            "status": "needs_information",
            "request": request,
            "questions": get_missing_questions(validation),
        }

    plan = create_plan(
    request,
    resources,
    farmer_location,
    )

    recommendation = generate_recommendation(plan)

    return {
        "status": "optimized",
        "request": request,
        "plan": plan,
        "recommendation": recommendation,
    }
