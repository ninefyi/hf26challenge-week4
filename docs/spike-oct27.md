# Spike, Oct 27: can a haunted zsh work, and how fast is Gemma?

All tests ran in a sandbox: `zsh -f` (no `~/.zshrc`, no oh-my-zsh), `HISTFILE=/dev/null`, driven through a pty by `spike/pty_test.py`. The real shell config was not touched.

## 1. zsh hooks (`sandbox/hook.zsh`)
- `preexec` and `precmd` record the command, exit code and duration. Spool lines showed `false` -> 1, `echo hi` -> 0, `sleep 1` -> 1.02 s.
- Cost: about **0.05 ms** per command for the hook itself (a spool write, no process started). A real engine call will add to this and must stay in the background.
- Caveat: `$?` is only correct if our `precmd` runs first, so the hook puts itself at the front of `precmd_functions`. With oh-my-zsh other hooks run too; this needs a re-check in the real shell.

## 2. Async display (`zle -F`)
A fake Whisper arrived 1.5 s after each command. It was printed above the prompt, and the prompt redrew cleanly. When a command was still running (`sleep 1`), earlier Whispers waited and appeared as soon as the prompt came back. No garbled prompt in this test. Not yet tried: long typed lines, tmux, other terminals.

## 3. History and secret hiding
- `revenant/history.py` parses zsh extended history (743 timestamped commands on the author's machine, Nov 2025 to Oct 2026).
- `revenant/redact.py` changed 113 of 743 commands (90 with URLs, 15 env secrets, 13 long tokens, 5 emails, 5 IPs). A crude check for leftover 32+ character strings found none. This is a check for obvious leaks, not a proof.
- 5 unit tests pass.

## 4. Gemma speed (fabricated cases, 10 per model, Apple M1 Pro 16 GB)
| Model | Cold first call | Warm median | Warm max |
|---|---|---|---|
| gemma3:4b | 6.0 s | 0.8 s | 0.9 s |
| gemma3:12b | 9.4 s | 3.0 s | 3.8 s |

Both are fine for an asynchronous Whisper.

## 5. Quality: first look (10 cases, judged by reading, not a proper eval)
- Both models write bland, mildly eerie lines. 12B writes better prose.
- **Both made factual mistakes about what happened**, so the "0 False claims" bar is hard.
  - 4B: said an `ssh` that exited with code 255 "succeeded", and called a failed `curl` a "server reported a failure".
  - 12B: said `npm install` happened "on a date far in the future" (the date given was in the past), and said "a day you can no longer recall" when the date was supplied.
- Lesson: do not let the model state facts. Let code state the facts (date, exit code, command) and the validator reject any line that contradicts them.

## Next
Decide the fact/flourish split, then build Memory retrieval, the Worth-a-Whisper rules and the validator.
