"""`python -m revenant ...`: whisper (called by the zsh hook), off, on, mute, status, stats."""
import argparse
import os
import sys
import time
from pathlib import Path

from revenant.ghost import Flourish, make_whisper, ollama_flourish, with_fallback
from revenant.history import Entry, load, load_spool, merge
from revenant.rules import norm
from revenant.state import State

DEFAULT_MODELS = "gemma3:12b,gemma3:4b"


def _flourish(recent: list[str]) -> Flourish:
    models = [m.strip() for m in os.environ.get("REVENANT_MODELS", DEFAULT_MODELS).split(",") if m.strip()]
    return with_fallback(*(ollama_flourish(m, recent=recent) for m in models))


def _whisper(args, st: State, flourish_fn: Flourish | None, stdin) -> int:
    command = stdin.read().strip()
    now = args.end or int(time.time())
    if not command or st.is_off():
        return 0
    started = time.time()
    record: dict = {"t": now}
    try:
        if st.is_muted(now):
            st.log({**record, "reason": "muted"})
            return 0
        path = Path(args.history or os.environ.get("REVENANT_HISTORY") or "~/.zsh_history").expanduser()
        history = merge(load(path) if path.exists() else [], load_spool(st.spool))
        history = [e for e in history if not (norm(e.command) == norm(command) and e.ts == args.start)]
        current = Entry(-1, args.start, args.dur, command, args.rc)
        result = make_whisper(
            current, history, now=now, flourish_fn=flourish_fn or _flourish(st.recent()),
            last_whisper_ts=st.last_whisper(), cooldown=int(os.environ.get("REVENANT_COOLDOWN", 180)),
        )
        record.update(reason=result.reason, ms=int((time.time() - started) * 1000))
        if result.problems:
            record["problems"] = [p.split(" (")[0].split(":")[0] for p in result.problems]
        if result.whisper:
            record["kind"] = result.whisper.kind
            st.set_last_whisper(now)
            st.add_recent(result.whisper.flourish)
            print(result.whisper.render())
    except Exception as exc:  # the Ghost never makes noise in your terminal
        record.update(reason="error", error=type(exc).__name__)
    st.log(record)
    return 0


def main(argv: list[str], *, flourish_fn: Flourish | None = None, stdin=None, state: State | None = None) -> int:
    p = argparse.ArgumentParser(prog="revenant", description="A haunted terminal. Read-only: never runs or edits anything.")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("whisper", help="called by the zsh hook; reads the command on stdin")
    w.add_argument("--start", type=int, required=True)
    w.add_argument("--end", type=int)
    w.add_argument("--rc", type=int, default=0)
    w.add_argument("--dur", type=int, default=0)
    w.add_argument("--history")
    sub.add_parser("off", help="switch the Ghost off until `revenant on`")
    sub.add_parser("on", help="switch the Ghost back on")
    m = sub.add_parser("mute", help="stay silent for a while")
    m.add_argument("minutes", type=int, nargs="?", default=60)
    sub.add_parser("unmute")
    sub.add_parser("status")
    sub.add_parser("stats", help="how often the Ghost spoke (no command text is logged)")
    args = p.parse_args(argv)

    st = state or State()
    if args.cmd == "whisper":
        return _whisper(args, st, flourish_fn, stdin or sys.stdin)
    if args.cmd == "off":
        st.set_off(True)
        print("revenant is off. `revenant on` to bring it back.")
    elif args.cmd == "on":
        st.set_off(False)
        print("revenant is on.")
    elif args.cmd == "mute":
        st.mute(int(time.time()) + args.minutes * 60)
        print(f"muted for {args.minutes} minutes.")
    elif args.cmd == "unmute":
        st.mute(None)
        print("unmuted.")
    elif args.cmd == "status":
        now = int(time.time())
        print("off" if st.is_off() else "muted" if st.is_muted(now) else "on", f"(state: {st.root})")
    elif args.cmd == "stats":
        print(st.stats())
    return 0
