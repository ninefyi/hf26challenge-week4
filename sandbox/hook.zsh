# revenant hook (spike). Source from a zsh session; never edits history, never runs anything from it.
zmodload zsh/datetime 2>/dev/null
typeset -g _rv_cmd _rv_t0

_rv_preexec() { _rv_cmd=$1; _rv_t0=$EPOCHREALTIME }

# Show a finished Whisper while the prompt is waiting (or at the next prompt if a command is running).
_rv_ready() {
  local fd=$1 line
  zle -F $fd
  read -r -u $fd line
  exec {fd}<&-
  [[ -n $line ]] || return 0
  zle -I
  print -rP -- "%F{244}${line}%f"
}

_rv_precmd() {
  local rc=$?
  [[ -n $_rv_cmd ]] || return 0
  local dur=$(( EPOCHREALTIME - _rv_t0 ))
  print -r -- "$EPOCHSECONDS	$rc	$dur	$_rv_cmd" >>| "${REVENANT_SPOOL:-/dev/null}"
  if [[ -n $REVENANT_FAKE_DELAY ]]; then
    local fd
    exec {fd}< <(sleep $REVENANT_FAKE_DELAY; print -r -- "👻 fake whisper for: ${_rv_cmd}")
    zle -F $fd _rv_ready
  fi
  _rv_cmd=
}

precmd_functions=(_rv_precmd $precmd_functions)
preexec_functions+=(_rv_preexec)
