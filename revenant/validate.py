"""Checks that run after the model has spoken. Any failure means the Ghost stays silent."""
import re
from dataclasses import dataclass
from datetime import tzinfo
from typing import Sequence

from revenant.facts import fact_line
from revenant.history import Entry
from revenant.rules import Trigger, norm, risky_kind


@dataclass(frozen=True)
class Whisper:
    kind: str
    memory_id: int
    count: int
    fact: str      # written by code
    flourish: str  # written by the model; must carry no facts

    def render(self) -> str:
        return f"👻 {self.flourish} {self.fact}"


# The flourish is atmosphere only. Anything that states a fact about time, outcome or history is banned.
_BANNED = re.compile(
    r"\b(?:succe\w*|fail\w*|error\w*|crash\w*|work(?:ed|s|ing)?|broke\w*|broken|exit\w*|code|delet\w*|eras\w*|"
    r"vanish\w*|destroy\w*|remov\w*|lost|gone|kill\w*|clean\w*|install\w*|complet\w*|finish\w*|done|ok|okay|"
    r"pass\w*|ran|run|runs|running|execut\w*|ago|yesterday|today|tonight|tomorrow|day|days|week|weeks|month|"
    r"months|year|years|hour|hours|minute|minutes|second|seconds|midnight|night|morning|evening|again|before|"
    r"previous\w*|last|first|once|twice|never|always|every|already|still|remember\w*|recall\w*|forgot\w*|"
    r"sudo|command|commands|history|terminal|shell)\b",
    re.I,
)


# Past tense reads as a claim about what happened ("filled", "restored"), so the flourish must use the present tense.
_PAST = re.compile(r"\b(?!(?:red|bed|need|seed|speed|shed|feed|hundred|indeed)\b)\w{2,}ed\b", re.I)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_]{3,}", text)}


def check_flourish(flourish: str, commands: Sequence[str]) -> list[str]:
    errs = []
    if not flourish.strip():
        errs.append("flourish is empty")
    if len(flourish) > 110:
        errs.append("flourish is too long")
    if len(re.findall(r"[.!?]", flourish)) > 2:
        errs.append("flourish has more than two sentences")
    if re.search(r"\d|`", flourish):
        errs.append("flourish contains a digit or a backtick")
    p = _PAST.search(flourish)
    if p:
        errs.append(f"flourish uses the past tense (word: {p.group(0)!r})")
    m = _BANNED.search(flourish)
    if m:
        errs.append(f"flourish states a fact (word: {m.group(0)!r})")
    shared = _tokens(flourish) & set().union(*(_tokens(c) for c in commands)) if commands else set()
    if shared:
        errs.append(f"flourish mentions part of a command ({sorted(shared)[0]!r})")
    return errs


def validate(
    w: Whisper,
    current: Entry,
    history: Sequence[Entry],
    *,
    now: int,
    tz: tzinfo | None = None,
) -> list[str]:
    """Return a list of problems; empty means the Whisper may be shown."""
    mem = next((e for e in history if e.id == w.memory_id), None)
    if mem is None:
        return ["memory is not in the history"]
    errs: list[str] = []
    if mem.ts > now:
        errs.append("memory is from the future")
    if w.kind == "risky":
        if risky_kind(mem.command) is None or risky_kind(mem.command) != risky_kind(current.command):
            errs.append("memory is not the same kind of risky command")
    elif norm(mem.command) != norm(current.command):
        errs.append("memory is not the same command")
    if w.kind == "failed_before" and mem.exit_code in (None, 0):
        errs.append("memory did not fail, or its exit code is unknown")
    try:
        expected = fact_line(Trigger(w.kind, mem, w.count), current.command, now, tz)
    except ValueError:
        return errs + ["unknown kind"]
    if w.fact != expected:
        errs.append("fact line does not match the memory")
    return errs + check_flourish(w.flourish, [current.command, mem.command])
