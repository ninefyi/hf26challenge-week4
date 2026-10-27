# revenant: source this file from zsh. The Ghost is read-only: it never runs or edits anything.
# Off switches: `revenant off`, `revenant mute 30`, or open a shell with `zsh -f`.
zmodload zsh/datetime 2>/dev/null
typeset -g _rv_cmd _rv_t0

: ${REVENANT_HOME:=${${(%):-%x}:A:h:h}}
: ${REVENANT_STATE:=$HOME/.local/state/revenant}
: ${REVENANT_PYTHON:=$REVENANT_HOME/.venv/bin/python}
export REVENANT_STATE REVENANT_HOME REVENANT_PYTHON
[[ -n $HISTFILE ]] && export REVENANT_HISTORY=${REVENANT_HISTORY:-$HISTFILE}
mkdir -p -m 700 -- $REVENANT_STATE

revenant() { PYTHONPATH=$REVENANT_HOME $REVENANT_PYTHON -m revenant "$@" }

_rv_preexec() { _rv_cmd=$1; _rv_t0=$EPOCHREALTIME }

# Print a finished Whisper above the prompt, or at the next prompt if a command is still running.
_rv_ready() {
  local fd=$1 line
  zle -F $fd
  read -r -u $fd line
  exec {fd}<&-
  [[ -n $line ]] || return 0
  zle -I
  print -r -- $'\e[2m'"$line"$'\e[0m'
}

_rv_precmd() {
  local rc=$?                                   # must be the first line: $? is the command's exit code
  [[ -n $_rv_cmd ]] || return 0
  local cmd=$_rv_cmd t0=$_rv_t0
  _rv_cmd=
  [[ $cmd == revenant(|[[:space:]]*) ]] && return 0
  [[ -e $REVENANT_STATE/off ]] && return 0
  local now=$EPOCHSECONDS dur=$(( EPOCHREALTIME - t0 )) start=${t0%.*}
  print -r -- "$start	$rc	$dur	${cmd//[$'\t\n']/ }" >>| $REVENANT_STATE/spool
  local fd
  exec {fd}< <(print -rn -- $cmd | PYTHONPATH=$REVENANT_HOME $REVENANT_PYTHON -m revenant whisper \
      --start $start --end $now --rc $rc --dur ${dur%.*} 2>/dev/null)
  zle -F $fd _rv_ready
}

precmd_functions=(_rv_precmd ${precmd_functions:#_rv_precmd})
preexec_functions=(${preexec_functions:#_rv_preexec} _rv_preexec)
