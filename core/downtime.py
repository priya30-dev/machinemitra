"""Downtime cost meter: turns "machine is down" into rupees, which is what a
factory owner (and an enterprise judge) actually cares about."""
from dataclasses import dataclass


@dataclass
class DowntimeInputs:
    idle_workers: int = 0
    wage_per_hour: float = 0.0        # ₹ per worker per hour
    lost_output_per_hour: float = 0.0  # ₹ of production not made per hour


def cost_per_hour(d: DowntimeInputs) -> float:
    return max(0.0, d.idle_workers * d.wage_per_hour + d.lost_output_per_hour)


def expected_loss(d: DowntimeInputs, hours_until_fixed: float) -> float:
    return round(cost_per_hour(d) * max(0.0, hours_until_fixed))


def bump_urgency(urgency: str, per_hour: float) -> str:
    """A very expensive stoppage is at least 'high'. Never lowers urgency."""
    if urgency in ("medium", "low") and per_hour >= 5000:
        return "high"
    return urgency


def inr(amount: float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if n < 0 else "") + "₹" + s
