"""How often does the validator accept a real Gemma flourish? Fabricated histories only."""
import sys, time
from datetime import timezone
from collections import Counter

from revenant.history import Entry
from revenant.ghost import make_whisper, ollama_flourish
from revenant.rules import DAY

UTC, NOW = timezone.utc, 1_800_000_000
SCENARIOS = {
    "failed_before": (Entry(9, NOW, 0, "make test"), [Entry(1, NOW - 3 * DAY, 4, "make test", 2)]),
    "risky": (Entry(9, NOW, 0, "git push --force origin main"), [Entry(1, NOW - 40 * DAY, 0, "git push -f")]),
    "returns": (Entry(9, NOW, 0, "docker compose up"), [Entry(1, NOW - 90 * DAY, 0, "docker compose up")]),
    "repeat": (Entry(9, NOW, 0, "npm test"), [Entry(1, NOW - 300, 0, "npm test"), Entry(2, NOW - 100, 0, "npm test")]),
}
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
model = sys.argv[1]
fn = ollama_flourish(model)
calls = Counter(); outcomes = Counter(); rejected = Counter(); samples = []
def counted(kind, fact, cur):
    calls[model] += 1
    out = fn(kind, fact, cur)
    return out
t0 = time.time()
for kind, (cur, hist) in SCENARIOS.items():
    for _ in range(REPS):
        r = make_whisper(cur, hist, now=NOW, flourish_fn=counted, tz=UTC)
        outcomes[r.reason] += 1
        for p in r.problems: rejected[p.split(" (")[0]] += 1
        if r.whisper: samples.append(r.whisper.render())
n = sum(outcomes.values())
print(f"{model}: {n} whispers tried, {calls[model]} model calls, {time.time()-t0:.0f}s total")
print("  outcomes:", dict(outcomes)); print("  last-attempt rejection reasons:", dict(rejected))
print("  first-try accept rate (n whispers / model calls):", f"{outcomes['ok']}/{calls[model]}")
for s in samples[:4]: print("  e.g.", s)
