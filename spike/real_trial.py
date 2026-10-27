"""Real trial: the user's real zsh config, real ~/.zsh_history (read-only), real Gemma (12B, 4B fallback).
HISTFILE=/dev/null so the test writes nothing to the real history; state goes to a scratch dir.
Only no-op shell functions stand in for brew/rm/make, so nothing real is executed or deleted."""
import os, pty, re, select, shutil, sys, time

scratch = sys.argv[1]
def trial(name, cmds, wait):
    state = os.path.join(scratch, "state"); shutil.rmtree(state, ignore_errors=True)
    env = {"HOME": os.environ["HOME"], "PATH": os.environ["PATH"], "TERM": "xterm-256color", "HISTFILE": "/dev/null",
           "REVENANT_STATE": state, "REVENANT_HISTORY": os.path.expanduser("~/.zsh_history")}
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(os.path.join(scratch, "cwd")); os.execvpe("zsh", ["zsh", "-i"], env)
    t0, buf = time.time(), []
    def drain(sec):
        end = time.time() + sec
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                try: d = os.read(fd, 8192)
                except OSError: return
                buf.append((time.time() - t0, d.decode(errors="replace")))
    def send(s): os.write(fd, s.encode())
    drain(4); send("brew(){return 0}; rm(){return 0}; make(){return 2}\n"); drain(0.5)
    marks = []
    for c, gap in cmds:
        marks.append((time.time() - t0, c)); send(c + "\n"); drain(gap)
    drain(wait); send("exit\n"); drain(1)
    print(f"\n=== {name}")
    for t, c in marks: print(f"  {t:5.1f}s typed: {c}")
    for t, s in buf:
        for line in re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07", "", s).splitlines():
            if "👻" in line or "alive" in line and "echo" not in line: print(f"  {t:5.1f}s {line.strip()[:210]}")
    lp = os.path.join(state, "log.ndjson")
    print("  log:", open(lp).read().strip().replace("\n", " | ") if os.path.exists(lp) else "(none)")

trial("A. returns: a command last run ~1 year ago (brew, no-op)", [("brew", 0.5), ("echo alive", 0.5)], 30)
trial("B. risky: rm -rf .rockbox (rm is a no-op here)", [("rm -rf .rockbox", 0.5), ("echo alive", 0.5)], 30)
trial("C. failed before: make test twice (exit 2)", [("make test", 0.5), ("make test", 1)], 30)
