# Working With AI — reader companion

Practice files for *Working With AI: A Practical Guide to Getting More Done* (second edition) by Varun Kaushik.

Everything here is fictional and runs on your own computer. Nothing connects to a work system, calls an AI model, schedules itself or sends a message. The automated checks validate these fixtures; they do not evaluate a model's answers or prove anything about a live system.

## What you need

- Python 3.10 or later, standard library only. Check with `python3 --version` (on Windows, `py -3 --version`).
- For Practice 5's shell demo only: a POSIX shell (macOS, Linux, or WSL on Windows).

## Get the files

Either clone this repository or download it as a ZIP (green **Code** button → **Download ZIP**), extract it, and open a terminal in the folder that contains `labs.py`.

## Run everything once

```
python3 -m unittest -v test_labs
```

Twenty-four checks should pass. If they do not, your Python is probably older than 3.10.

## Where each file is used

| Book section | Command or file | What to expect |
| --- | --- | --- |
| Practice 1 (Ch 11) | `data/meeting.txt`, `answer_keys/practice-1.md` | Paste the transcript into an AI tool; compare with the key |
| Practice 2 (Ch 11) | `python3 labs.py costs` | Total 150 → 220, +70, 46.67% |
| Practice 4 (Ch 11) | `data/proposal_notes.txt`, `answer_keys/practice-4.md` | Draft a proposal with `[TBC]` markers |
| Chapter 14 | `python3 labs.py roi`; `data/worksheet.csv` | 1.67 h / $73.33 and −1.00 h / −$55.00 |
| Chapter 21 | `python3 labs.py report`, then again | `created`, then `already_created`; draft in `work/` |
| Chapter 22 | `python3 labs.py search --user reader "annual leave allowance"` | Quote from `leave-v2`, 22 days |
| Practice 3 (Ch 23) | `python3 labs.py state` | One `link_existing` action, `cloud_changes: 0`; `--file data/state_conflict.json` stops with exit 2 |
| Practice 5 (Ch 23) | `sh shared_input_demo.sh buggy` / `fixed`; `python3 labs.py coverage` / `--fixed` | Buggy run fails with exit 2; fixed passes |
| Chapters 8, 24 | `templates.md` | Review record, evidence card, tooling disclosure, publishing checklist |

Practices 1, 2 and 4 need no code beyond the one `costs` command. Chapters 19 to 24 are Part Two of the book, for readers who build and run systems.

## Exit codes

`0` means pass or created. `2` means a check failed or the program stopped for review. A stop is the program working, not breaking.

## Reporting a problem

Open an issue in this repository. Say which book section, which command, and what you saw.

## Licence

Code is MIT licensed (see `LICENSE`). The fictional text, data and answer keys may be copied and adapted for personal study and teaching with attribution to the book.
