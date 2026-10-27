"""End to end in a sandboxed zsh: hook -> engine -> real Gemma -> Whisper above the prompt.
Commands are harmless shell functions; no real docker/git/make runs. Usage: e2e_pty.py <history> <state-dir>"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from pty_test import run

hist, state = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
hook = os.path.abspath("shell/revenant.zsh")
setup = "docker(){return 0}; git(){return 0}; make(){return 2}\n"

def scenario(name, cmds, total):
    shutil.rmtree(state, ignore_errors=True)
    env = {"REVENANT_STATE": state, "REVENANT_HISTORY": hist, "REVENANT_MODELS": "gemma3:4b"}
    steps = [(0.4, setup), (0.2, f"source {hook}\n")] + [(d, c + "\n") for d, c in cmds]
    print(f"\n=== {name}")
    for t, s in run(steps, env, total=total):
        if "👻" in s or "revenant" in s.lower() and "source" not in s:
            print(f"{t:5}s {s.strip()[:200]!r}")
    print("log:", open(os.path.join(state, "log.ndjson")).read().strip().replace("\n", " | ")[:400] if os.path.exists(os.path.join(state, "log.ndjson")) else "(none)")

scenario("returns after months (docker compose up)", [(0.5, "ls"), (0.5, "docker compose up"), (0.3, "echo next")], 14)
scenario("failed before (make test twice)", [(0.5, "make test"), (1.0, "make test")], 14)
scenario("off switch", [(0.5, "revenant off"), (1.5, "docker compose up")], 8)
