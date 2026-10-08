"""Conversation session management for KisanPool AI."""

from __future__ import annotations

from typing import Any


class ConversationSession:
    """Stores the current request for one farmer conversation."""

    def __init__(self) -> None:
        self.current_request: dict[str, Any] | None = None

    def update(self, request: dict[str, Any]) -> None:
        """Store the latest merged request."""
        self.current_request = request

    def get(self) -> dict[str, Any] | None:
        """Return the current request."""
        return self.current_request

    def clear(self) -> None:
        """Reset the conversation."""
        self.current_request = None