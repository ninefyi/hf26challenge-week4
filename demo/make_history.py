"""Write a FABRICATED zsh history for the demo, with dates relative to now. Nothing here is a real command."""
import sys, time
now, day = int(time.time()), 86400
rows = [(120, "ls -la"), (90, "docker compose up"), (60, "npm run build"), (40, "git push -f"), (30, "make test"),
        (20, "git status"), (12, "npm test"), (6, "git log --oneline"), (3, "cd ~/projects/demo-app")]
with open(sys.argv[1], "w") as f:
    for d, cmd in rows:
        f.write(f": {now - d * day}:0;{cmd}\n")
