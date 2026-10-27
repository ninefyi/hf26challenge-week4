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
    exit_code: int | None = None  # zsh history does not store it; only the hook's spool does


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


def load_spool(path: str | Path) -> list[Entry]:
    """Read the hook's spool: `<epoch>\t<exit code>\t<seconds>\t<command>` per line.
    Ids start at 1_000_000 so they never clash with history ids."""
    p = Path(path).expanduser()
    if not p.exists():
        return []
    out = []
    for i, line in enumerate(p.read_text(errors="replace").splitlines()):
        parts = line.split("\t", 3)
        if len(parts) != 4 or not parts[3].strip():
            continue
        try:
            ts, rc, dur = int(parts[0]), int(parts[1]), int(float(parts[2]))
        except ValueError:
            continue
        out.append(Entry(1_000_000 + i, ts, dur, parts[3].strip(), rc))
    return out


def _n(command: str) -> str:
    return " ".join(command.split())


def merge(history: list[Entry], spool: list[Entry], window: int = 120) -> list[Entry]:
    """History plus spool, oldest first. zsh also logs commands the hook saw, so a history
    entry with the same command within `window` seconds of a spool entry is dropped
    (the spool one knows the exit code)."""
    def dup(h: Entry) -> bool:
        return any(_n(s.command) == _n(h.command) and abs(s.ts - h.ts) <= window for s in spool)

    return sorted([h for h in history if not dup(h)] + spool, key=lambda e: (e.ts, e.id))
