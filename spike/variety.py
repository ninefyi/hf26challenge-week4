"""Does the rotating image stop the Ghost repeating itself? 12B, fabricated history, validator on."""
import collections, sys, time
from datetime import timezone
from revenant.history import Entry
from revenant.ghost import make_whisper, ollama_flourish, with_fallback
from revenant.rules import DAY

NOW = 1_800_000_000
cur, hist = Entry(9, NOW, 0, "docker compose up"), [Entry(1, NOW - 90 * DAY, 0, "docker compose up")]
recent, lines, silent, t0 = [], [], 0, time.time()
for _ in range(int(sys.argv[1])):
    fn = with_fallback(ollama_flourish("gemma3:12b", recent=recent))
    r = make_whisper(cur, hist, now=NOW, flourish_fn=fn, tz=timezone.utc)
    if r.whisper:
        lines.append(r.whisper.flourish); recent.append(r.whisper.flourish)
    else:
        silent += 1
first = collections.Counter(l.split()[0].lower().strip(",.") for l in lines)
print(f"{len(lines)} shown, {silent} silent, {time.time()-t0:.0f}s; distinct lines {len(set(lines))}; most common first words: {first.most_common(4)}")
for l in lines[:8]: print(" -", l)
