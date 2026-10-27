# What revenant adds to a machine, and how to remove it

| What | Where | Remove |
|---|---|---|
| One `source` line (plus a comment) at the end of `~/.zshrc` | `~/.zshrc` | Delete those two lines, or `cp ~/.zshrc.bak-before-revenant ~/.zshrc` |
| Backup of the original `~/.zshrc` | `~/.zshrc.bak-before-revenant` | `rm` it once you no longer need it |
| State: spool (**contains commands**), log (no commands), switches | `~/.local/state/revenant/` | `rm -rf ~/.local/state/revenant` |
| The project itself and its virtualenv | `~/revenant/` | `rm -rf ~/revenant` |
| Gemma 3 12B and 4B (already installed before this project) | Ollama | Keep, or `ollama rm gemma3:12b gemma3:4b`; free memory with `ollama stop gemma3:12b` |
| Demo tools, installed by `brew install vhs` on 2026-10-27 | Homebrew | see below |

## Homebrew formulae added for the demo (15)
`dav1d ffmpeg lame libevent libvmaf libvpx libwebsockets mpg123 opus sdl2-compat sdl3 svt-av1 ttyd vhs x264 x265`

```bash
brew uninstall vhs ttyd ffmpeg && brew autoremove
```
`brew autoremove` removes the libraries nothing else needs. Check `brew list` afterwards: any of the 15 you also use for something else will stay.

## A quick check that it is gone
```bash
zsh -i -c 'type revenant'     # expect: revenant not found
ls ~/.local/state/revenant    # expect: No such file or directory
```
Your `~/.zsh_history` is never edited by revenant.
