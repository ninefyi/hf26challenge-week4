from revenant.history import parse

TEXT = ": 1700000000:0;git status\n: 1700000100:3;echo one \\\ntwo\n: 1700000200:0;\n: 1700000300:0;ls\n"


def test_parses_entries_with_timestamps():
    es = parse(TEXT)
    assert [e.command for e in es] == ["git status", "echo one \\\ntwo", "ls"]
    assert es[0].ts == 1700000000 and es[1].duration == 3


def test_empty_commands_are_dropped_and_ids_are_stable():
    assert [e.id for e in parse(TEXT)] == [0, 1, 3]
