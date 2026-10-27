"""Eval against the Accuracy bar (0 Invented memories, 0 False claims).
Real set: commands from ~/.zsh_history, read-only, treated as if re-run now. Fabricated set: clearly labelled cases
for risky / failed-before / repeat, because old history has no exit codes and few risky commands.
The ORACLE re-checks every fact line against the raw history text with its own regexes, not the validator's code.
Detail (with redacted real commands) goes to eval-real/ (git-ignored); only aggregate numbers are printed."""
import collections, json, random, re, statistics, sys, time
from datetime import datetime
from pathlib import Path

from revenant.ghost import make_whisper, ollama_flourish, with_fallback
from revenant.history import Entry, load
from revenant.redact import redact
from revenant.rules import DAY, norm, risky_kind
from revenant.validate import Whisper, validate

NOW = int(time.time())
N_REAL = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUT = Path("eval-real"); OUT.mkdir(exist_ok=True)

def stamp(ts, fmt): return datetime.fromtimestamp(ts).strftime(fmt)

# ---- the oracle: raw text in, claims checked, no revenant.history / validate code involved
def raw_tuples(path):
    out = []
    for line in Path(path).expanduser().read_text(errors="replace").splitlines():
        m = re.match(r"^: (\d+):\d+;(.*)$", line)
        if m: out.append((int(m.group(1)), None, m.group(2)))
    return out

def oracle(fact, tuples):
    """Return [] if every claim in the fact line is true of `tuples`; else the reasons it is not."""
    t = [(ts, rc, redact(norm(c))) for ts, rc, c in tuples if ts <= NOW]
    m = re.fullmatch(r"It has been (\d+) days since you ran `(.+)` \((\d{4}-\d\d-\d\d)\)\.", fact)
    if m:
        runs = [x for x in t if x[2] == m[2]]
        if not runs: return ["invented memory"]
        last = max(runs)
        return [] if (stamp(last[0], "%Y-%m-%d") == m[3] and (NOW - last[0]) // DAY == int(m[1])) else ["false claim: date/days"]
    m = re.fullmatch(r"The last time you ran something like this was (\d{4}-\d\d-\d\d \d\d:\d\d): `(.+)`\.", fact)
    if m:
        ok = any(x[2] == m[2] and stamp(x[0], "%Y-%m-%d %H:%M") == m[1] for x in t)
        return [] if ok else ["invented memory"]
    m = re.fullmatch(r"Last time you ran `(.+)` \((\d{4}-\d\d-\d\d \d\d:\d\d)\) it exited with code (-?\d+)\.", fact)
    if m:
        ok = any(x[2] == m[1] and stamp(x[0], "%Y-%m-%d %H:%M") == m[2] and x[1] == int(m[3]) for x in t)
        return [] if ok else ["invented memory or false exit code"]
    m = re.fullmatch(r"That is run number (\d+) of `(.+)` in ten minutes; the first was at (\d\d:\d\d)\.", fact)
    if m:
        runs = sorted(x for x in t if x[2] == m[2] and NOW - x[0] <= 600)
        ok = runs and len(runs) + 1 >= int(m[1]) and stamp(runs[0][0], "%H:%M") == m[3]
        return [] if ok else ["false claim: repeat"]
    return ["unrecognised fact line"]

# ---- cases
cases = []  # (label, set, current Entry, entries, tuples)
hist_path = "~/.zsh_history"
real = load(hist_path)
real_raw = raw_tuples(hist_path)
skip = lambda e: e.ts >= 1793068700 and e.ts <= 1793069100          # my own test lines, if still present
real = [e for e in real if not skip(e)]
real_raw = [x for x in real_raw if not (1793068700 <= x[0] <= 1793069100)]
distinct = {}
for e in real:
    if len(e.command) < 80 and "\n" not in e.command: distinct[norm(e.command)] = e
risky_real = [c for c in distinct if risky_kind(c)]
others = sorted(c for c in distinct if not risky_kind(c)); random.Random(2026).shuffle(others)
for c in (risky_real + others)[:N_REAL]:
    cases.append(("real", c, Entry(-1, NOW, 0, c), real, real_raw))

def fab(label, cur, rows):
    es = [Entry(i, ts, 0, c, rc) for i, (ts, rc, c) in enumerate(rows)]
    cases.append(("fabricated", label, Entry(-1, NOW, 0, cur), es, [(ts, rc, c) for ts, rc, c in rows]))
for i, (cmd, d) in enumerate([("git push --force origin main", 40), ("git reset --hard HEAD~3", 12), ("rm -rf node_modules", 90),
        ("psql -c 'DROP TABLE users'", 200), ("chmod -R 777 /srv/app", 33), ("dd if=/dev/zero of=disk.img", 70),
        ("git push -f", 5), ("rm -rf ./dist", 61), ("psql -c 'TRUNCATE TABLE orders'", 18), ("git reset --hard origin/main", 300)]):
    fab(f"fab risky {i}", cmd, [(NOW - d * DAY, 0, cmd)])
for i, (cmd, rc) in enumerate([("make test", 2), ("npm run build", 1), ("curl localhost:8080/health", 7)]):
    fab(f"fab failed {i}", cmd, [(NOW - 3 * DAY, rc, cmd)])
for i, cmd in enumerate(["npm test", "docker compose up"]):
    fab(f"fab repeat {i}", cmd, [(NOW - 400, 0, cmd), (NOW - 200, 0, cmd)])

# ---- run
fn = with_fallback(ollama_flourish("gemma3:12b"), ollama_flourish("gemma3:4b"))
rows, reasons, kinds, bad, lat = [], collections.Counter(), collections.Counter(), [], []
for src, label, cur, entries, tuples in cases:
    t0 = time.time()
    r = make_whisper(cur, entries, now=NOW, flourish_fn=fn)
    dt = time.time() - t0
    reasons[(src, r.reason)] += 1
    rec = {"problems": [x.split(" (")[0] + (" " + x.split("word: ")[1].rstrip(")") if "word: " in x else "") for x in r.problems], "set": src, "label": label if src == "fabricated" else redact(label), "reason": r.reason, "s": round(dt, 1)}
    if r.whisper:
        w = r.whisper; kinds[(src, w.kind)] += 1; lat.append(dt)
        problems = oracle(w.fact, tuples)
        if problems: bad.append((src, w.kind, problems))
        rec.update(kind=w.kind, fact=w.fact, flourish=w.flourish, oracle=problems or "ok")
    rows.append(rec)
(OUT / "results.ndjson").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))

shown = sum(v for (s, k), v in reasons.items() if k == "ok")
print(f"cases: {len(cases)} ({sum(1 for c in cases if c[0]=='real')} real, {sum(1 for c in cases if c[0]=='fabricated')} fabricated)")
print("outcomes:", {f"{s}/{k}": v for (s, k), v in sorted(reasons.items())})
print("shown by kind:", {f"{s}/{k}": v for (s, k), v in sorted(kinds.items())})
print(f"ORACLE: {shown} whispers checked, {len(bad)} with an invented memory or false claim in the fact line {bad if bad else ''}")
if lat: print(f"time per shown whisper: median {statistics.median(lat):.1f}s, max {max(lat):.1f}s")
why = collections.Counter(p for r in rows for p in r["problems"] if r["reason"] == "invalid")
print("why silent after 3 tries:", dict(why))
print("flourishes shown (review these by eye):")
for r in rows:
    if r["reason"] == "ok": print("  -", r["flourish"])
