import io
import stat

from revenant.cli import main
from revenant.state import State

NOW = 1_800_000_000
DAY = 86400


def run(argv, tmp_path, fn=None, command="docker compose up"):
    st = State(tmp_path / "state")
    return main(argv, flourish_fn=fn, stdin=io.StringIO(command), state=st), st


def history_file(tmp_path, lines):
    f = tmp_path / "hist"
    f.write_text("".join(f": {ts}:0;{cmd}\n" for ts, cmd in lines))
    return str(f)


def whisper_args(hist, **kw):
    return ["whisper", "--start", str(NOW - 5), "--end", str(NOW), "--history", hist]


def test_state_is_private_and_switches_work(tmp_path):
    st = State(tmp_path / "s")
    assert stat.S_IMODE(st.root.stat().st_mode) == 0o700
    st.set_off(True); assert st.is_off()
    st.set_off(False); assert not st.is_off()
    st.mute(NOW + 60); assert st.is_muted(NOW) and not st.is_muted(NOW + 61)
    st.mute(None); assert not st.is_muted(NOW)
    for i in range(10):
        st.add_recent(f"line {i}")
    assert st.recent() == [f"line {i}" for i in range(2, 10)]


def test_whisper_prints_a_line_when_there_is_a_memory(tmp_path, capsys):
    hist = history_file(tmp_path, [(NOW - 90 * DAY, "docker compose up")])
    rc, st = run(whisper_args(hist), tmp_path, fn=lambda k, f, c: "Fog gathers at the door.")
    out = capsys.readouterr().out
    assert rc == 0 and out.startswith("👻 Fog gathers at the door. It has been 90 days since you ran `docker compose up`")
    assert st.last_whisper() == NOW and st.recent() == ["Fog gathers at the door."]


def test_log_holds_no_command_text(tmp_path, capsys):
    hist = history_file(tmp_path, [(NOW - 90 * DAY, "docker compose up")])
    _, st = run(whisper_args(hist), tmp_path, fn=lambda k, f, c: "Fog gathers at the door.")
    text = (st.root / "log.ndjson").read_text()
    assert "docker" not in text and '"reason": "ok"' in text and '"kind": "returns"' in text


def test_silent_when_off_muted_or_nothing_to_say(tmp_path, capsys):
    hist = history_file(tmp_path, [(NOW - 90 * DAY, "docker compose up")])
    fn = lambda k, f, c: "Fog gathers at the door."
    st = State(tmp_path / "state")
    st.set_off(True)
    run(whisper_args(hist), tmp_path, fn)
    assert capsys.readouterr().out == "" and st.read_log() == []
    st.set_off(False); st.mute(NOW + 600)
    run(whisper_args(hist), tmp_path, fn)
    assert capsys.readouterr().out == "" and st.read_log()[-1]["reason"] == "muted"
    st.mute(None)
    run(whisper_args(hist), tmp_path, fn, command="ls")
    assert capsys.readouterr().out == "" and st.read_log()[-1]["reason"] == "not worth"


def test_cooldown_after_a_whisper(tmp_path, capsys):
    hist = history_file(tmp_path, [(NOW - 90 * DAY, "docker compose up")])
    fn = lambda k, f, c: "Fog gathers at the door."
    run(whisper_args(hist), tmp_path, fn)
    capsys.readouterr()
    run(whisper_args(hist), tmp_path, fn)
    assert capsys.readouterr().out == ""


def test_model_down_means_silence_not_noise(tmp_path, capsys):
    hist = history_file(tmp_path, [(NOW - 90 * DAY, "docker compose up")])
    def down(k, f, c):
        raise ConnectionRefusedError("no ollama")
    rc, st = run(whisper_args(hist), tmp_path, fn=down)
    assert rc == 0 and capsys.readouterr().out == "" and st.read_log()[-1]["reason"] == "model error"


def test_the_current_command_is_not_its_own_memory(tmp_path, capsys):
    # zsh and the hook both record the run that is happening right now; it must not count as a past run
    hist = history_file(tmp_path, [(NOW - 5, "docker compose up")])
    st = State(tmp_path / "state")
    st.spool.write_text(f"{NOW - 5}\t0\t3\tdocker compose up\n")
    run(whisper_args(hist), tmp_path, fn=lambda k, f, c: "Fog gathers at the door.")
    assert capsys.readouterr().out == ""


def test_stats_summarises_the_log(tmp_path):
    st = State(tmp_path / "s")
    for r in ({"reason": "ok", "kind": "risky", "ms": 3000}, {"reason": "not worth"}, {"reason": "not worth"}):
        st.log(r)
    text = st.stats()
    assert "commands seen: 3" in text and "whispers shown: 1" in text and "risky 1" in text
