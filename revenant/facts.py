"""The factual half of a Whisper. Written by code from a real Memory, never by the model."""
from datetime import datetime, tzinfo

from revenant.redact import redact
from revenant.rules import DAY, Trigger


def _when(ts: int, tz: tzinfo | None) -> str:
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")


def fact_line(trigger: Trigger, current_command: str, now: int, tz: tzinfo | None = None) -> str:
    m = trigger.memory
    cur = redact(current_command)
    mem = redact(m.command)
    if trigger.kind == "failed_before":
        return f"Last time you ran `{cur}` ({_when(m.ts, tz)}) it exited with code {m.exit_code}."
    if trigger.kind == "risky":
        return f"The last time you ran something like this was {_when(m.ts, tz)}: `{mem}`."
    if trigger.kind == "repeat":
        return f"That is run number {trigger.count} of `{cur}` in ten minutes; the first was at {_when(m.ts, tz)[11:]}."
    if trigger.kind == "returns":
        return f"It has been {(now - m.ts) // DAY} days since you ran `{cur}` ({_when(m.ts, tz)[:10]})."
    if trigger.kind == "late_night":
        return f"It is {datetime.fromtimestamp(now, tz).strftime('%H:%M')}. You last ran `{cur}` on {_when(m.ts, tz)}."
    raise ValueError(f"unknown trigger kind: {trigger.kind}")
