"""Time Gemma 3 12B vs 4B writing one Whisper. Fabricated cases only (safe to publish)."""
import json, statistics, sys, time, urllib.request

SYSTEM = ("You are the Ghost of the user's own shell history. Write ONE or TWO short, eerie, dry sentences in English. "
          "Use only the facts given. Never invent a command or a date. Never be cruel. No advice. "
          'Reply as JSON: {"whisper": "..."}')
CASES = [
    ("git push --force origin main", "git push --force origin main", "2026-08-14 02:10", 1),
    ("npm install", "npm install", "2026-05-03 21:40", 1),
    ("docker compose up", "docker compose up", "2026-03-09 09:12", 0),
    ("rm -rf build", "rm -rf build", "2026-06-21 23:55", 0),
    ("ssh prod-db", "ssh prod-db", "2026-07-02 03:30", 255),
    ("pip install torch", "pip install torch", "2026-02-11 14:05", 1),
    ("make test", "make test", "2026-09-30 17:20", 2),
    ("curl localhost:8080/health", "curl localhost:8080/health", "2026-08-01 11:00", 7),
    ("brew upgrade", "brew upgrade", "2025-11-03 09:22", 0),
    ("git reset --hard HEAD~3", "git reset --hard HEAD~3", "2026-06-18 01:47", 0),
]

def ask(model, cmd, mem, when, rc):
    prompt = f"Command just run: {cmd}\nMemory: you ran `{mem}` on {when}, and it exited with code {rc}."
    body = json.dumps({"model": model, "system": SYSTEM, "prompt": prompt, "stream": False, "format": "json",
                       "options": {"temperature": 0.7, "num_predict": 80}, "keep_alive": "10m"}).encode()
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"}), timeout=300))
    return time.time() - t, r["response"]

for model in sys.argv[1:]:
    times, lines = [], []
    for i, case in enumerate(CASES):
        dt, out = ask(model, *case)
        times.append(dt); lines.append(out)
        print(f"{model} #{i} {dt:5.1f}s {out.strip()[:170]}", flush=True)
    warm = times[1:]
    print(f"== {model}: first (cold) {times[0]:.1f}s | warm median {statistics.median(warm):.1f}s max {max(warm):.1f}s\n", flush=True)
