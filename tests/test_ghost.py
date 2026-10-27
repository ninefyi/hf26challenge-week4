from datetime import timezone

from revenant.facts import fact_line
from revenant.ghost import make_whisper
from revenant.history import Entry
from revenant.rules import DAY, Trigger
from revenant.validate import Whisper, check_flourish, validate

UTC = timezone.utc
NOW = 1_800_000_000  # 2027-01-15 08:00 UTC
CUR = Entry(9, NOW, 0, "make test", None)
PAST = Entry(1, NOW - 3 * DAY, 4, "make test", 2)


def whisper(flourish="Something stirs in the dust."):
    fact = fact_line(Trigger("failed_before", PAST), CUR.command, NOW, UTC)
    return Whisper("failed_before", PAST.id, 1, fact, flourish)


def test_fact_line_states_only_what_the_memory_says():
    t = Trigger("failed_before", PAST)
    assert fact_line(t, "make test", NOW, UTC) == "Last time you ran `make test` (2027-01-12 08:00) it exited with code 2."


def test_fact_line_hides_secrets_in_commands():
    t = Trigger("risky", Entry(1, NOW - DAY, 0, "rm -rf /srv/API_TOKEN=abc123", 0))
    assert "abc123" not in fact_line(t, "rm -rf build", NOW, UTC)


def test_valid_whisper_passes():
    assert validate(whisper(), CUR, [PAST], now=NOW, tz=UTC) == []


def test_invented_memory_is_rejected():
    w = whisper()
    assert validate(w, CUR, [], now=NOW, tz=UTC) == ["memory is not in the history"]
    ghost_memory = Whisper("failed_before", 77, 1, w.fact, w.flourish)
    assert validate(ghost_memory, CUR, [PAST], now=NOW, tz=UTC) == ["memory is not in the history"]


def test_wrong_date_or_exit_code_in_the_fact_is_rejected():
    w = whisper()
    bad = Whisper(w.kind, w.memory_id, w.count, w.fact.replace("2027-01-12", "2027-01-11"), w.flourish)
    assert "fact line does not match the memory" in validate(bad, CUR, [PAST], now=NOW, tz=UTC)
    bad = Whisper(w.kind, w.memory_id, w.count, w.fact.replace("code 2", "code 0"), w.flourish)
    assert "fact line does not match the memory" in validate(bad, CUR, [PAST], now=NOW, tz=UTC)


def test_failed_before_with_unknown_exit_code_is_rejected():
    unknown = Entry(1, NOW - DAY, 0, "make test", None)
    w = Whisper("failed_before", 1, 1, "Last time you ran `make test` (2027-01-14 08:00) it exited with code None.", "Dust gathers.")
    assert "memory did not fail, or its exit code is unknown" in validate(w, CUR, [unknown], now=NOW, tz=UTC)


def test_memory_must_be_the_same_command():
    other = Entry(1, NOW - DAY, 0, "make build", 1)
    t = Trigger("failed_before", other)
    w = Whisper("failed_before", 1, 1, fact_line(t, "make test", NOW, UTC), "Dust gathers.")
    assert "memory is not the same command" in validate(w, CUR, [other], now=NOW, tz=UTC)


def test_flourish_may_not_state_facts():
    cmds = ["make test"]
    assert check_flourish("Something stirs in the dust.", cmds) == []
    assert check_flourish("A red lantern sways; the bed creaks.", cmds) == []
    for bad in [
        "It failed again.",             # outcome and history
        "You were here three days ago.",  # time
        "The tests were there in 2026.",  # digit and command word
        "The server succeeded.",
        "Last time was worse.",
        "",
        "One. Two. Three.",
        "x" * 120,
        "The disk filled up.",        # past tense reads as a claim about what happened
        "Everything was restored.",
    ]:
        assert check_flourish(bad, cmds), bad


def test_pipeline_speaks_when_everything_checks_out():
    r = make_whisper(CUR, [PAST], now=NOW, flourish_fn=lambda k, f, c: "Something stirs in the dust.", tz=UTC)
    assert r.reason == "ok" and r.whisper.render().startswith("👻 Something stirs")
    assert r.whisper.fact in r.whisper.render()


def test_pipeline_stays_silent_on_bad_flourish_after_retries():
    calls = []
    def liar(k, f, c):
        calls.append(1)
        return "It failed three days ago."
    r = make_whisper(CUR, [PAST], now=NOW, flourish_fn=liar, tz=UTC)
    assert r.whisper is None and r.reason == "invalid" and len(calls) == 3


def test_pipeline_retries_once_then_succeeds():
    answers = iter(["It failed again.", "A cold draft drifts by."])
    r = make_whisper(CUR, [PAST], now=NOW, flourish_fn=lambda k, f, c: next(answers), tz=UTC)
    assert r.reason == "ok"


def test_pipeline_stays_silent_when_the_model_is_down():
    def down(k, f, c):
        raise ConnectionRefusedError("ollama is not running")
    r = make_whisper(CUR, [PAST], now=NOW, flourish_fn=down, tz=UTC)
    assert r.whisper is None and r.reason == "model error"


def test_pipeline_stays_silent_when_nothing_is_worth_saying():
    r = make_whisper(Entry(9, NOW, 0, "ls", None), [Entry(1, NOW - DAY, 0, "ls", None)], now=NOW, flourish_fn=lambda *a: "x", tz=UTC)
    assert r.whisper is None and r.reason == "not worth"


def test_fallback_uses_the_next_model_only_when_the_first_fails():
    from revenant.ghost import with_fallback

    def down(k, f, c):
        raise TimeoutError("12b too slow")

    assert with_fallback(down, lambda k, f, c: "from 4b")("x", "y", "z") == "from 4b"
    assert with_fallback(lambda k, f, c: "from 12b", lambda k, f, c: "from 4b")("x", "y", "z") == "from 12b"
    try:
        with_fallback(down, down)("x", "y", "z")
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected the last error")
