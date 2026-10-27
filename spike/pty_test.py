"""Drive an interactive zsh in a pty (no real config) and record when output appears."""
import os, pty, select, sys, time

def run(steps, env_extra=None, total=8.0):
    env = {"HOME": os.environ["HOME"], "PATH": os.environ["PATH"], "TERM": "xterm", "PS1": "PROMPT> ",
           "HISTFILE": "/dev/null", **(env_extra or {})}
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe("zsh", ["zsh", "-f", "-i"], env)
    t0 = time.time(); out = []
    def drain(until):
        while time.time() < until:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                try: data = os.read(fd, 4096)
                except OSError: return
                if data: out.append((round(time.time() - t0, 2), data.decode(errors="replace")))
    for delay, text in steps:
        drain(time.time() + delay)
        os.write(fd, text.encode())
    drain(t0 + total)
    os.write(fd, b"exit\n"); drain(time.time() + 0.3)
    return out

if __name__ == "__main__":
    hook = os.path.abspath("shell/revenant.zsh")
    spool = "/tmp/revenant-spool-spike"
    open(spool, "w").close()
    steps = [(0.5, f"source {hook}\n"), (0.5, "false\n"), (0.5, "echo hi\n"), (0.3, "sleep 1\n")]
    for t, s in run(steps, {"REVENANT_SPOOL": spool, "REVENANT_FAKE_DELAY": "1.5"}):
        print(f"{t:5}s {s!r}")
    print("--- spool ---"); print(open(spool).read())
