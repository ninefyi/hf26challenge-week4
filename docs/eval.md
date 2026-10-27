# Eval against the Accuracy bar (Oct 27)

**Bar, fixed before testing:** 0 Invented memories and 0 False claims. Run with `PYTHONPATH=. uv run python eval/run_eval.py 30` and `eval/adversarial.py`. Real commands and their whispers are kept in `eval-real/` (git-ignored); this file has numbers only.

## Set
- **30 real commands** from the author's own `~/.zsh_history` (read-only), treated as if re-run now; all 4 distinct risky ones are included. 19 of the 30 had something worth saying (a command last run 60+ days ago, or a risky one with an earlier match); 11 were not worth a whisper, as designed.
- **15 fabricated cases**, labelled as such, because old history has no exit codes and few risky commands: 10 risky, 3 "failed before", 2 repeats.
- Model: Gemma 3 12B (4B as fallback), up to 3 tries per whisper.

## An independent oracle
`run_eval.py` re-checks every fact line against the raw history text with its own regexes, not the validator's code (it shares only the secret-hiding function and the local-time convention). It checks that the cited command and date exist, that the day count and exit code match, and that the memory is the latest earlier run.

## Results
| Run | What changed | Whispers shown (of 34 eligible) | Silent after tries | Oracle: invented memory / false claim in the fact line |
|---|---|---|---|---|
| 1 | validator only, 2 tries | 16 | 18 | 0 |
| 2 | prompt told not to refer to the past or memory, 3 tries | 34 | 0 | 0 |
| 3 | present-tense rule added to the validator | 34 | 0 | 0 |

- Time per shown whisper (run 3): median 2.8 s, max 10.3 s.
- Run 1 was silent so often because Gemma, playing a ghost of your history, loved words like "once", "remembers" and "forgotten", which the validator bans. Fixing the prompt, not loosening the validator, solved it. Runs 2 and 3 used the same set that I tuned on, so "34 of 34" is not a held-out result.
- I read the flourishes from runs 2 and 3 by eye; none states a fact about a command. A few are borderline in tone ("hands now absent", "observing your hand's slow drift"). The author should read them too.
- Repetition is not solved: "Dust" opens about half of the lines in the eval, which runs without the "avoid recent lines" memory the real Ghost has.

## Trying to trick the validator (`eval/adversarial.py`, no model)
| Attack | Caught |
|---|---|
| Tampered fact line: memory that is not in the history, a different command, a memory from the future, wrong exit code, wrong year, wrong kind, an extra claim glued on | 7 of 7 |
| Flourish stating a fact in words the blocklist knows ("It failed again", "three days ago", a digit, a command name, empty) | 14 of 14 |
| Past-tense sneaky lie ("The disk filled up.") after adding the present-tense rule | 6 of 6 |
| **Present-tense sneaky lie ("The disk is full.", "Nothing breaks.")**, written after the rule | **0 of 6** |

## What this means
- The **fact line** is safe by construction: code writes it from a real entry and the validator recomputes it. No invented memory or wrong date or exit code got through.
- The **flourish** is only safe against what I thought to ban. A blocklist plus a tense rule cannot stop a model from saying "The disk is full." The bar of 0 False claims holds for the fact line; for the flourish it holds on everything I tried and by eye, and I know of a way around it. The post should say so.
