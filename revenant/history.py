"""Read a zsh extended-history file. Read-only: nothing here writes to the file."""
import re
from dataclasses import dataclass
from pathlib import Path

_START = re.compile(r"^: (\d+):(\d+);(.*)$")


@dataclass(frozen=True)
class Entry:
    id: int
    ts: int
    duration: int
    command: str


def parse(text: str) -> list[Entry]:
    """Parse `: <epoch>:<duration>;<command>` lines. Lines that do not start an entry
    continue the previous command (zsh stores multi-line commands that way)."""
    raw: list[list] = []
    for line in text.splitlines():
        m = _START.match(line)
        if m:
            raw.append([int(m.group(1)), int(m.group(2)), m.group(3)])
        elif raw:
            raw[-1][2] += "\n" + line
    return [Entry(i, ts, dur, cmd.strip()) for i, (ts, dur, cmd) in enumerate(raw) if cmd.strip()]


def load(path: str | Path) -> list[Entry]:
    return parse(Path(path).expanduser().read_text(errors="replace"))
