# A throwaway shell for recording the demo. Nothing from your real ~/.zshrc is loaded.
PS1='%F{green}demo%f %~ $ '
HISTFILE=/dev/null
setopt NO_BEEP INTERACTIVE_COMMENTS
# docker/git/make/npm are stand-in scripts in demo/bin (first on PATH, set by record.sh), never the real ones.
export PATH="$REVENANT_SRC/demo/bin:$PATH"
export REVENANT_STATE="${DEMO_STATE:-/tmp/revenant-demo-state}"
export REVENANT_HISTORY="${DEMO_HISTORY:-/tmp/revenant-demo-history}"
export REVENANT_COOLDOWN=1
export REVENANT_MODELS="gemma3:12b,gemma3:4b"
source "${REVENANT_SRC}/shell/revenant.zsh"
