"""Decide whether a command is worth a Whisper, and which Memory it points at.
Everything here is plain code. The model is never asked to remember anything."""
import re
from dataclasses import dataclass
from typing import Sequence

from revenant.history import Entry

DAY = 86400

# Things that deserve a pause. Each kind has a name so "like this" can be matched across commands.
RISKY = {
    "force-push": re.compile(r"\bgit\s+push\b.*(?:\s--force(?:-with-lease)?\b|\s-f\b)"),
    "hard-reset": re.compile(r"\bgit\s+reset\b.*\s--hard\b"),
    "recursive-delete": re.compile(r"\brm\s+(?:-\S+\s+)*-(?:\w*[rR]\w*|-recursive)\b"),
    "drop-data": re.compile(r"\b(?:drop\s+(?:table|database)|truncate\s+table)\b", re.I),
    "disk-write": re.compile(r"\b(?:dd\s+if=|mkfs\b|diskutil\s+erase)"),
    "recursive-permissions": re.compile(r"\b(?:chmod|chown)\s+(?:-\S+\s+)*-R\b"),
}


@dataclass(frozen=True)
class Trigger:
    kind: str  # failed_before | risky | repeat | returns | late_night
    memory: Entry
    count: int = 1


def norm(command: str) -> str:
    return " ".join(command.split())


def risky_kind(command: str) -> str | None:
    for name, pattern in RISKY.items():
        if pattern.search(command):
            return name
    return None


def decide(
    current: Entry,
    history: Sequence[Entry],
    *,
    now: int,
    last_whisper_ts: int | None = None,
    cooldown: int = 180,
    months_days: int = 60,
    repeat_window: int = 600,
    repeat_min: int = 3,
    local_hour: int | None = None,
) -> Trigger | None:
    """Return the reason to whisper, or None to stay silent. `history` must not include `current`."""
    if last_whisper_ts is not None and now - last_whisper_ts < cooldown:
        return None
    past = sorted((e for e in history if e.ts <= now and e.id != current.id), key=lambda e: (e.ts, e.id))
    same = [e for e in past if norm(e.command) == norm(current.command)]

    failed = [e for e in same if e.exit_code not in (None, 0)]
    if failed:
        return Trigger("failed_before", failed[-1])

    kind = risky_kind(current.command)
    if kind:
        like = [e for e in past if risky_kind(e.command) == kind]
        if like:
            return Trigger("risky", like[-1])

    recent = [e for e in same if now - e.ts <= repeat_window]
    if len(recent) + 1 >= repeat_min:
        return Trigger("repeat", recent[0], count=len(recent) + 1)

    if same and now - same[-1].ts >= months_days * DAY:
        return Trigger("returns", same[-1])

    if local_hour is not None and 0 <= local_hour < 5 and same:
        return Trigger("late_night", same[-1])

    return None
