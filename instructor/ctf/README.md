# Cross Creek 101 — capstone CTF

Optional, self-paced, done after Session 7. Nine flags. Each is a value the
student can only produce by actually running the attack or the defense against
the range, not by reading the book.

## For the student

1. Bring the range up: `./start.sh` (flags 1–6 and 9) and later `./start.sh --segmented` (flags 7–8).
2. Work `tasks.md`.
3. Put your answers in a file, one per line:
   ```
   flag1=...
   flag2=...
   ```
4. Score it: `./check-flags.sh submission.txt`

## For the instructor

- `answers.txt` holds the expected values and the match type (exact / numeric-min / regex).
- `check-flags.sh` reads it; keep `answers.txt` out of the student handout.
- Nothing here plants a literal `FLAG{...}` string in the range. The "flags"
  are observed values, so the CTF cannot be solved by grepping the repo.
