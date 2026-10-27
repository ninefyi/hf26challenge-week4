from revenant.history import parse

TEXT = ": 1700000000:0;git status\n: 1700000100:3;echo one \\\ntwo\n: 1700000200:0;\n: 1700000300:0;ls\n"


def test_parses_entries_with_timestamps():
    es = parse(TEXT)
    assert [e.command for e in es] == ["git status", "echo one \\\ntwo", "ls"]
    assert es[0].ts == 1700000000 and es[1].duration == 3


def test_empty_commands_are_dropped_and_ids_are_stable():
    assert [e.id for e in parse(TEXT)] == [0, 1, 3]


def test_spool_gives_exit_codes_and_merge_prefers_it(tmp_path):
    from revenant.history import Entry, load_spool, merge

    spool = tmp_path / "spool"
    spool.write_text("1700000100\t2\t1.5\tmake test\nbroken line\n1700000200\tx\t0\tbad rc\n")
    s = load_spool(spool)
    assert [(e.command, e.exit_code, e.id) for e in s] == [("make test", 2, 1_000_000)]
    assert load_spool(tmp_path / "missing") == []

    hist = [Entry(0, 1700000000, 0, "ls"), Entry(1, 1700000090, 1, "make test")]
    merged = merge(hist, s)
    assert [(e.command, e.exit_code) for e in merged] == [("ls", None), ("make test", 2)]
