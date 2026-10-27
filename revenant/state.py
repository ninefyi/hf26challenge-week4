"""Small files the Ghost keeps between commands. Holds no command text except the spool,
which is private to the user (directory mode 700)."""
import json
import os
import statistics
from collections import Counter
from pathlib import Path


def default_root() -> Path:
    return Path(os.environ.get("REVENANT_STATE") or "~/.local/state/revenant").expanduser()


class State:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else default_root()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)

    @property
    def spool(self) -> Path:
        return self.root / "spool"

    def _int(self, name: str) -> int | None:
        try:
            return int((self.root / name).read_text().strip())
        except (OSError, ValueError):
            return None

    # off switch and mute
    def is_off(self) -> bool:
        return (self.root / "off").exists()

    def set_off(self, off: bool) -> None:
        flag = self.root / "off"
        flag.touch() if off else flag.unlink(missing_ok=True)

    def mute(self, until: int | None) -> None:
        f = self.root / "mute"
        f.write_text(str(until)) if until else f.unlink(missing_ok=True)

    def is_muted(self, now: int) -> bool:
        until = self._int("mute")
        return until is not None and now < until

    # what the Ghost last said
    def last_whisper(self) -> int | None:
        return self._int("last_whisper")

    def set_last_whisper(self, ts: int) -> None:
        (self.root / "last_whisper").write_text(str(ts))

    def recent(self) -> list[str]:
        try:
            return list(json.loads((self.root / "recent.json").read_text()))
        except (OSError, ValueError):
            return []

    def add_recent(self, flourish: str, keep: int = 8) -> None:
        (self.root / "recent.json").write_text(json.dumps((self.recent() + [flourish])[-keep:]))

    # one log line per command: no command text, only what happened
    def log(self, record: dict) -> None:
        with open(self.root / "log.ndjson", "a") as f:
            f.write(json.dumps(record) + "\n")

    def read_log(self) -> list[dict]:
        try:
            lines = (self.root / "log.ndjson").read_text().splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def stats(self) -> str:
        log = self.read_log()
        if not log:
            return "no commands logged yet"
        reasons = Counter(r.get("reason", "?") for r in log)
        kinds = Counter(r["kind"] for r in log if r.get("kind"))
        spoke = reasons.get("ok", 0)
        ms = [r["ms"] for r in log if r.get("reason") in ("ok", "invalid") and "ms" in r]
        lines = [f"commands seen: {len(log)}", f"whispers shown: {spoke} ({100 * spoke / len(log):.1f}%)",
                 "outcomes: " + ", ".join(f"{k} {v}" for k, v in reasons.most_common())]
        if kinds:
            lines.append("shown by kind: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
        if ms:
            lines.append(f"model time when asked: median {statistics.median(ms) / 1000:.1f}s, max {max(ms) / 1000:.1f}s")
        return "\n".join(lines)
