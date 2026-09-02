#!/usr/bin/env bash
# Score a Cross Creek CTF submission.
#   ./check-flags.sh submission.txt
# submission.txt has lines like  flag1=admin
set -uo pipefail
cd "$(dirname "$0")"

SUB="${1:-submission.txt}"
KEY="answers.txt"

[ -f "$SUB" ] || { echo "no submission file: $SUB" >&2; exit 2; }
[ -f "$KEY" ] || { echo "missing answers.txt (instructor only)" >&2; exit 2; }

norm() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^ *//;s/ *$//'; }

score=0
total=0
while IFS='|' read -r flag mtype expected; do
  case "$flag" in ''|\#*) continue ;; esac
  flag="$(norm "$flag")"; mtype="$(norm "$mtype")"
  expected="$(printf '%s' "$expected" | sed 's/^ *//;s/ *$//')"
  total=$((total + 1))

  given="$(grep -iE "^${flag}=" "$SUB" | head -1 | cut -d= -f2- )"
  given_n="$(norm "$given")"
  ok=0
  case "$mtype" in
    exact)  [ "$given_n" = "$(norm "$expected")" ] && ok=1 ;;
    one-of) for o in $(printf '%s' "$expected" | tr '|' ' '); do
              [ "$given_n" = "$(norm "$o")" ] && ok=1
            done ;;
    regex)  printf '%s' "$given" | grep -qE "$expected" && ok=1 ;;
    *)      echo "unknown match type '$mtype' for $flag" >&2 ;;
  esac

  if [ "$ok" -eq 1 ]; then
    printf '  [+] %-6s correct\n' "$flag"
    score=$((score + 1))
  else
    printf '  [x] %-6s wrong or missing (got: %s)\n' "$flag" "${given:-<none>}"
  fi
done < "$KEY"

echo
echo "score: $score / $total"
[ "$score" -eq "$total" ]
