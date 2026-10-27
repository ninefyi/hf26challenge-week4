"""One Whisper, end to end: decide, state the facts, ask the model for a flourish, validate."""
import json
import random
import urllib.request
from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Callable, Sequence

from revenant.facts import fact_line
from revenant.history import Entry
from revenant.redact import redact
from revenant.rules import decide
from revenant.validate import Whisper, check_flourish, validate

Flourish = Callable[[str, str, str], str]  # (kind, fact line, redacted current command) -> flourish

SYSTEM = (
    "You are the Ghost of the user's own shell history. Write ONE short, eerie, dry sentence of atmosphere, "
    "at most 12 words, in English. State no facts: no dates, numbers, times, commands, outcomes or counts, "
    "and never say whether anything worked, failed, ran, was last or first. Never be cruel. Give no advice. "
    "Use the present tense only, with no word ending in -ed. Do not refer to the past, memory, remembering, forgetting, or 'once'. "
    'Reply as JSON: {"flourish": "..."}'
)

# A different image each time keeps the Ghost from saying "dust motes" forever.
IMAGES = (
    "fog", "a candle flame", "a stopped clock", "a moth at a window", "cobwebs", "a cellar door", "a lantern",
    "the tide", "a staircase", "a cracked mirror", "a crow", "static on a radio", "rain on glass", "an empty chair",
    "a music box", "an attic", "a distant bell", "frost", "a draught under the door", "old wallpaper",
)


def ollama_flourish(
    model: str = "gemma3:12b",
    url: str = "http://localhost:11434",
    timeout: float = 25,
    recent: Sequence[str] = (),
    rng: random.Random | None = None,
) -> Flourish:
    rng = rng or random.Random()

    def ask(kind: str, fact: str, current: str) -> str:
        prompt = f"Image to draw on: {rng.choice(IMAGES)}. Write only the atmospheric sentence."
        if recent:
            prompt += " Do not reuse the wording or the first word of these earlier lines: " + " | ".join(recent[-5:])
        body = json.dumps({
            "model": model, "system": SYSTEM, "prompt": prompt, "stream": False, "format": "json",
            "options": {"temperature": 0.9, "num_predict": 60}, "keep_alive": "10m",
        }).encode()
        req = urllib.request.Request(f"{url}/api/generate", body, {"Content-Type": "application/json"})
        reply = json.load(urllib.request.urlopen(req, timeout=timeout))["response"]
        return str(json.loads(reply).get("flourish", "")).strip()

    return ask


def with_fallback(*fns: Flourish) -> Flourish:
    """Try each model in turn (12B first, then 4B). Raise only if every one fails."""
    def call(kind: str, fact: str, current: str) -> str:
        last: Exception | None = None
        for fn in fns:
            try:
                return fn(kind, fact, current)
            except Exception as exc:
                last = exc
        raise last or RuntimeError("no model configured")

    return call


@dataclass(frozen=True)
class Result:
    whisper: Whisper | None
    reason: str  # ok | not worth | model error | invalid
    problems: tuple[str, ...] = ()


def make_whisper(
    current: Entry,
    history: Sequence[Entry],
    *,
    now: int,
    flourish_fn: Flourish,
    tz: tzinfo | None = None,
    last_whisper_ts: int | None = None,
    attempts: int = 3,
) -> Result:
    local_hour = datetime.fromtimestamp(now, tz).hour
    trigger = decide(current, history, now=now, last_whisper_ts=last_whisper_ts, local_hour=local_hour)
    if trigger is None:
        return Result(None, "not worth")
    fact = fact_line(trigger, current.command, now, tz)
    problems: list[str] = []
    for _ in range(attempts):
        try:
            text = flourish_fn(trigger.kind, fact, redact(current.command))
        except Exception as exc:  # Ollama down, timeout, bad JSON: the Ghost just stays quiet
            return Result(None, "model error", (f"{type(exc).__name__}: {exc}",))
        w = Whisper(trigger.kind, trigger.memory.id, trigger.count, fact, text)
        problems = validate(w, current, history, now=now, tz=tz)
        if not problems:
            return Result(w, "ok")
    return Result(None, "invalid", tuple(problems))
