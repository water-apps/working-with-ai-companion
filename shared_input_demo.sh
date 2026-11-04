#!/bin/sh
# Practice 5: a loop whose worker shares the loop's input stream.
# Usage: sh shared_input_demo.sh buggy | fixed
# Fictional accounts; nothing is copied anywhere.
mode="${1:-buggy}"
tmp="$(mktemp)"
printf 'demo-a\ndemo-b\ndemo-c\n' > "$tmp"
started=0
expected=3

worker() {
  # Simulates a worker that reads whatever is on its standard input.
  python3 -c 'import sys; sys.stdin.read()'
}

while IFS= read -r name; do
  echo "processed $name"
  if [ "$mode" = "fixed" ]; then
    worker </dev/null      # the worker gets an empty input of its own
  else
    worker                 # BUG: the worker inherits the loop's input and eats the remaining names
  fi
  started=$((started + 1))
done < "$tmp"
rm -f "$tmp"

echo "started $started of $expected"
if [ "$started" -ne "$expected" ]; then
  echo "FAIL: incomplete coverage"
  exit 2
fi
exit 0
