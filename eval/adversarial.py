"""Try to trick the validator. No model involved: hand-written bad Whispers go straight in."""
import time
from revenant.facts import fact_line
from revenant.history import Entry
from revenant.rules import DAY, Trigger
from revenant.validate import Whisper, validate

NOW = int(time.time())
CUR = Entry(-1, NOW, 0, "make test", None)
MEM = Entry(1, NOW - 3 * DAY, 4, "make test", 2)
OTHER = Entry(2, NOW - 2 * DAY, 0, "make build", 1)
FUT = Entry(3, NOW + 3600, 0, "make test", 1)
HIST = [MEM, OTHER, FUT]
good_fact = fact_line(Trigger("failed_before", MEM), CUR.command, NOW)

def w(flourish="Something stirs in the dust.", kind="failed_before", mid=1, count=1, fact=good_fact):
    return Whisper(kind, mid, count, fact, flourish)

def caught(x): return bool(validate(x, CUR, HIST, now=NOW))

groups = {
  "tampered fact line (code or data wrong)": [
    w(mid=99),                                               # memory that is not in the history
    w(mid=2),                                                # a real entry, but a different command
    w(mid=3),                                                # an entry from the future
    w(fact=good_fact.replace("code 2", "code 0")),           # wrong exit code
    w(fact=good_fact.replace(str(MEM.ts and "") or "20", "19", 1)),  # wrong year
    w(kind="risky"),                                         # wrong kind for this memory
    w(fact=good_fact + " It also deleted your files."),      # extra claim glued onto the fact
  ],
  "flourish that states a fact (blocklist words)": [w(f) for f in (
    "It failed again, as it did yesterday.", "Three days ago this crashed.", "The command succeeded last time.",
    "You were here in 2026.", "It deleted everything before.", "Exit code 1 haunts you.", "The server never answered.",
    "Last night it all went wrong.", "It worked, once.", "You ran this a week ago.", "`make test` echoes in the dark.",
    "The tests are gone.", "One. Two. Three.", "")],
  "sneaky, past tense (the -ed rule is aimed at these)": [w(f) for f in (
    "The disk filled up.", "Your files returned unharmed.", "The server answered happily.", "Everything was restored.",
    "The database exploded.", "Someone pushed to the wrong branch.")],
  "sneaky, present tense (written after the -ed rule; nothing aims at these)": [w(f) for f in (
    "The disk is full.", "The server answers.", "Everything comes back.", "The database explodes.",
    "Someone pushes to the wrong branch.", "Nothing breaks.")],
}
total_c = total = 0
for name, items in groups.items():
    c = sum(caught(x) for x in items); total_c += c; total += len(items)
    print(f"{name}: caught {c} of {len(items)}")
    for x in items:
        if not caught(x): print("   NOT caught:", repr(x.flourish if x.fact == good_fact else x.fact[-40:]))
