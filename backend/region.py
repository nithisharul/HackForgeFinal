"""Region switch: "us" (the original CMS-style dataset) or "in" (the PM-JAY-style India dataset).

The code is shared; each region keeps its own raw data, processed outputs, trained models and
Second Brain, so nothing written for one region is ever read by the other. The active region is
held in a context variable: the API sets it per request and the pipeline sets it per run, and
everything defaults to "us" so existing callers behave exactly as before.
"""
import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
Code = Literal["us", "in"]
# India: the state government owns every public hospital, which is not a shared-owner signal.
PUBLIC_OWNERS = {"GOV"}


@dataclass(frozen=True)
class Region:
    code: str
    name: str
    raw: Path
    proc: Path
    reference: Path
    know: Path
    models: Path

    def money(self, x):
        return inr(x) if self.code == "in" else f"${x:,.0f}"


def inr(x):
    """Rupees with Indian digit grouping: 1234567 -> ₹12,34,567."""
    digits = str(abs(round(x)))
    head, groups = digits[:-3], [digits[-3:]]
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ("-" if x < 0 else "") + "₹" + ",".join(groups)


REGIONS = {
    "us": Region("us", "United States", ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "data" / "reference",
                 ROOT / "knowledge", ROOT / "backend" / "models"),
    "in": Region("in", "India (PM-JAY)", ROOT / "data" / "india" / "raw", ROOT / "data" / "india" / "processed",
                 ROOT / "data" / "india" / "reference", ROOT / "knowledge" / "india", ROOT / "backend" / "models" / "india"),
}
_active = contextvars.ContextVar("region", default="us")


def current():
    return REGIONS[_active.get()]


@contextmanager
def use(code):
    token = _active.set(code)
    try:
        yield REGIONS[code]
    finally:
        _active.reset(token)
