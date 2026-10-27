from revenant.history import Entry
from revenant.rules import DAY, decide, risky_kind

NOW = 1_800_000_000


def e(id, ts, cmd, rc=None):
    return Entry(id, ts, 0, cmd, rc)


def test_risky_kinds():
    assert risky_kind("git push --force origin main") == "force-push"
    assert risky_kind("git push -f") == "force-push"
    assert risky_kind("git reset --hard HEAD~3") == "hard-reset"
    assert risky_kind("rm -rf build") == "recursive-delete"
    assert risky_kind("rm -fr build") == "recursive-delete"
    assert risky_kind("rm build.log") is None
    assert risky_kind("rm -f build.log") is None
    assert risky_kind("git push origin main") is None
    assert risky_kind("psql -c 'DROP TABLE users'") == "drop-data"


def test_silent_by_default():
    cur = e(9, NOW, "ls")
    assert decide(cur, [e(1, NOW - 5 * DAY, "ls")], now=NOW) is None
    assert decide(cur, [], now=NOW) is None


def test_failed_before_needs_a_known_exit_code():
    cur = e(9, NOW, "make test")
    hist = [e(1, NOW - DAY, "make test", rc=2)]
    t = decide(cur, hist, now=NOW)
    assert t.kind == "failed_before" and t.memory.id == 1
    # zsh history has no exit codes: an unknown past outcome is never called a failure
    assert decide(cur, [e(1, NOW - DAY, "make test")], now=NOW) is None
    assert decide(cur, [e(1, NOW - DAY, "make test", rc=0)], now=NOW) is None


def test_risky_points_at_the_last_command_of_the_same_kind():
    cur = e(9, NOW, "git push --force origin main")
    hist = [e(1, NOW - 90 * DAY, "git push -f"), e(2, NOW - 3 * DAY, "git push --force-with-lease")]
    t = decide(cur, hist, now=NOW)
    assert t.kind == "risky" and t.memory.id == 2
    assert decide(cur, [e(3, NOW - DAY, "git reset --hard")], now=NOW) is None  # nothing like it before


def test_repeat_counts_the_current_run():
    cur = e(9, NOW, "npm test")
    hist = [e(1, NOW - 400, "npm test"), e(2, NOW - 200, "npm test")]
    t = decide(cur, hist, now=NOW)
    assert t.kind == "repeat" and t.count == 3 and t.memory.id == 1
    assert decide(cur, hist[1:], now=NOW) is None  # only 2 runs


def test_returns_after_months_only_for_the_same_command():
    cur = e(9, NOW, "docker compose up")
    assert decide(cur, [e(1, NOW - 80 * DAY, "docker compose up")], now=NOW).kind == "returns"
    assert decide(cur, [e(1, NOW - 10 * DAY, "docker compose up")], now=NOW) is None
    assert decide(cur, [e(1, NOW - 80 * DAY, "docker compose down")], now=NOW) is None


def test_late_night_needs_a_memory_of_the_same_command():
    cur = e(9, NOW, "ssh prod")
    hist = [e(1, NOW - 10 * DAY, "ssh prod")]
    assert decide(cur, hist, now=NOW, local_hour=2).kind == "late_night"
    assert decide(cur, hist, now=NOW, local_hour=14) is None
    assert decide(cur, [], now=NOW, local_hour=2) is None


def test_cooldown_and_future_entries():
    cur = e(9, NOW, "git push -f")
    hist = [e(1, NOW - DAY, "git push --force")]
    assert decide(cur, hist, now=NOW, last_whisper_ts=NOW - 60) is None
    assert decide(cur, hist, now=NOW, last_whisper_ts=NOW - 600).kind == "risky"
    assert decide(cur, [e(2, NOW + 100, "git push -f")], now=NOW) is None  # a memory cannot be from the future
