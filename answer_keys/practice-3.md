# Practice 3 answer key — missing state link

Reference: `python3 labs.py state`.

Expected plan: exactly one action — `link_existing`, address `database.a`, resource `demo/account-a`. `cloud_changes: 0`. No file is written.

Why: account A exists in the inventory, so creating it is not justified. Account B is already tracked correctly, so it needs nothing.

Conflict case: `python3 labs.py state --file data/state_conflict.json` must stop for review (exit 2) because `database.b` is tracked against `demo/account-a`. A tool that quietly rewrites the mapping has failed the exercise.

This is an analogy, not Terraform. A real import writes state and needs the right backend, identity, address and a fresh plan.
