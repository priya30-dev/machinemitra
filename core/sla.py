"""Service-level deadlines: how soon a technician must arrive, by urgency.
Maintenance contractors sell exactly this promise to factories."""
import time

ARRIVAL_HOURS = {"critical": 2, "high": 4, "medium": 24, "low": 72}


def due_at(urgency: str, created: float | None = None) -> float:
    return (time.time() if created is None else created) + ARRIVAL_HOURS.get(urgency, 24) * 3600


def remaining(due: float, now: float | None = None) -> float:
    """Seconds left (negative when overdue)."""
    return due - (time.time() if now is None else now)


def describe(due: float, status: str, now: float | None = None) -> tuple[str, str]:
    """Return (label, state) where state is ok | soon | overdue | met."""
    if status in ("on_site", "fixed"):
        return "SLA met", "met"
    left = remaining(due, now)
    if left < 0:
        return f"Overdue by {_fmt(-left)}", "overdue"
    return f"{_fmt(left)} left", "soon" if left < 3600 else "ok"


def _fmt(seconds: float) -> str:
    m = int(seconds // 60)
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h < 48 else f"{h // 24} days"
