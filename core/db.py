"""SQLite storage for machines, tickets and ticket events.

Ticket lifecycle:  open -> assigned -> on_the_way -> on_site -> fixed
Events record every change (status, technician voice updates, service report),
so the board shows a full timeline per ticket.

On Streamlit Community Cloud the disk resets on restart — fine for a demo; a
production deployment would point DB_PATH at a managed Postgres instead."""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

import config
from core import sla

STATUSES = ["open", "assigned", "on_the_way", "on_site", "fixed"]
STATUS_LABELS = {"open": "Open", "assigned": "Assigned", "on_the_way": "On the way",
                 "on_site": "On site", "fixed": "Fixed"}
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS machines (
  id TEXT PRIMARY KEY, factory_id TEXT, name TEXT, machine_type TEXT, model TEXT, installed INTEGER);
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created REAL, factory_id TEXT, machine_id TEXT, machine_type TEXT,
  urgency TEXT, status TEXT, escalated INTEGER DEFAULT 0, escalation_reason TEXT,
  technician_id TEXT, due_at REAL, language TEXT,
  transcript TEXT, ticket_json TEXT,
  cost_per_hour REAL, expected_loss REAL, api_cost REAL, snr_db REAL, seconds_to_ticket REAL,
  fixed_at REAL, report_json TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, ts REAL, kind TEXT,
  text TEXT, audio BLOB);
"""


def _path() -> str:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    return os.path.join(config.CACHE_DIR, "machinemitra.db")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM machines").fetchone()[0] == 0:
        with open(os.path.join(config.DATA_DIR, "machines.json"), encoding="utf-8") as f:
            for m in json.load(f)["machines"]:
                conn.execute("INSERT INTO machines VALUES (?,?,?,?,?,?)",
                             (m["id"], m["factory_id"], m["name"], m["machine_type"], m["model"], m["installed"]))
        conn.commit()
    return conn


@contextmanager
def _db():
    """Open, commit and always close a connection."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in ("ticket_json", "report_json"):
        if d.get(k):
            d[k.replace("_json", "")] = json.loads(d[k])
    return d


# ---------- machines ----------
def machines(factory_id: str | None = None) -> list[dict]:
    with _db() as c:
        q = "SELECT * FROM machines" + (" WHERE factory_id=?" if factory_id else "") + " ORDER BY id"
        return [dict(r) for r in c.execute(q, (factory_id,) if factory_id else ())]


def machine(machine_id: str) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        return dict(r) if r else None


# ---------- tickets ----------
def create_ticket(*, factory_id: str, machine_id: str | None, ticket: dict, transcript: str,
                  technician_id: str | None, language: str, cost_per_hour: float = 0,
                  expected_loss: float = 0, api_cost: float = 0, snr_db: float | None = None,
                  seconds_to_ticket: float = 0, escalated: bool = False, escalation_reason: str = "") -> int:
    now = time.time()
    status = "assigned" if technician_id else "open"
    with _LOCK, _db() as c:
        cur = c.execute(
            """INSERT INTO tickets (created, factory_id, machine_id, machine_type, urgency, status, escalated,
               escalation_reason, technician_id, due_at, language, transcript, ticket_json, cost_per_hour,
               expected_loss, api_cost, snr_db, seconds_to_ticket)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (now, factory_id, machine_id, ticket.get("machine_type", "unknown").lower(), ticket.get("urgency", "medium"),
             status, int(escalated), escalation_reason, technician_id, sla.due_at(ticket.get("urgency", "medium"), now),
             language, transcript, json.dumps(ticket, ensure_ascii=False), cost_per_hour, expected_loss,
             api_cost, snr_db, seconds_to_ticket))
        tid = cur.lastrowid
        c.execute("INSERT INTO events (ticket_id, ts, kind, text) VALUES (?,?,?,?)",
                  (tid, now, "created", f"Ticket created ({status})"))
        return tid


def update_ticket(ticket_id: int, *, ticket: dict, transcript: str, technician_id: str | None, language: str,
                  cost_per_hour: float, expected_loss: float, api_cost: float, escalated: bool,
                  escalation_reason: str, note: str = "Ticket updated") -> None:
    """Refresh a ticket after the caller answers follow-up questions."""
    with _LOCK, _db() as c:
        c.execute("""UPDATE tickets SET machine_type=?, urgency=?, technician_id=?, language=?, transcript=?,
                     ticket_json=?, cost_per_hour=?, expected_loss=?, api_cost=api_cost+?, escalated=?,
                     escalation_reason=? WHERE id=?""",
                  (ticket.get("machine_type", "unknown").lower(), ticket.get("urgency", "medium"), technician_id,
                   language, transcript, json.dumps(ticket, ensure_ascii=False), cost_per_hour, expected_loss,
                   api_cost, int(escalated), escalation_reason, ticket_id))
        c.execute("INSERT INTO events (ticket_id, ts, kind, text) VALUES (?,?,?,?)",
                  (ticket_id, time.time(), "updated", note))


def get_ticket(ticket_id: int) -> dict | None:
    with _db() as c:
        return _row(c.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())


def list_tickets(status: str | None = None, factory_id: str | None = None, limit: int = 200) -> list[dict]:
    q, args = "SELECT * FROM tickets WHERE 1=1", []
    if status:
        q += " AND status=?"
        args.append(status)
    if factory_id:
        q += " AND factory_id=?"
        args.append(factory_id)
    q += " ORDER BY created DESC LIMIT ?"
    args.append(limit)
    with _db() as c:
        return [_row(r) for r in c.execute(q, args)]


def set_status(ticket_id: int, status: str, note: str = "", audio: bytes | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unknown status {status}")
    now = time.time()
    with _LOCK, _db() as c:
        c.execute("UPDATE tickets SET status=?, fixed_at=CASE WHEN ?='fixed' THEN ? ELSE fixed_at END WHERE id=?",
                  (status, status, now, ticket_id))
        c.execute("INSERT INTO events (ticket_id, ts, kind, text, audio) VALUES (?,?,?,?,?)",
                  (ticket_id, now, "status", f"{STATUS_LABELS[status]}" + (f" — {note}" if note else ""), audio))


def add_event(ticket_id: int, kind: str, text: str, audio: bytes | None = None) -> None:
    with _LOCK, _db() as c:
        c.execute("INSERT INTO events (ticket_id, ts, kind, text, audio) VALUES (?,?,?,?,?)",
                  (ticket_id, time.time(), kind, text, audio))


def events(ticket_id: int) -> list[dict]:
    with _db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM events WHERE ticket_id=? ORDER BY ts", (ticket_id,))]


def save_report(ticket_id: int, report: dict) -> None:
    with _LOCK, _db() as c:
        c.execute("UPDATE tickets SET report_json=? WHERE id=?", (json.dumps(report, ensure_ascii=False), ticket_id))


def escalate(ticket_id: int, reason: str) -> None:
    with _LOCK, _db() as c:
        c.execute("UPDATE tickets SET escalated=1, escalation_reason=? WHERE id=?", (reason, ticket_id))


# ---------- history helpers ----------
def recent_for_machine(factory_id: str, machine_id: str | None, machine_type: str, days: int = 30) -> list[dict]:
    cutoff = time.time() - days * 86400
    with _db() as c:
        if machine_id:
            rows = c.execute("SELECT * FROM tickets WHERE machine_id=? AND created>=? ORDER BY created DESC",
                             (machine_id, cutoff))
        else:
            rows = c.execute("SELECT * FROM tickets WHERE factory_id=? AND machine_type=? AND created>=? "
                             "ORDER BY created DESC", (factory_id, machine_type.lower(), cutoff))
        return [_row(r) for r in rows]


def open_ticket_for(factory_id: str, machine_id: str | None, machine_type: str, hours: int = 24) -> dict | None:
    """An unfixed ticket for the same machine in the last day = a repeat call."""
    for t in recent_for_machine(factory_id, machine_id, machine_type, days=1):
        if t["status"] != "fixed" and time.time() - t["created"] < hours * 3600:
            return t
    return None
