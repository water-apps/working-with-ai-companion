# Practice 5 answer key — make incomplete work fail visibly

`sh shared_input_demo.sh buggy` → `processed demo-a`, `started 1 of 3`, `FAIL: incomplete coverage`, exit 2. The worker inherited the loop's input and consumed the remaining names.

`sh shared_input_demo.sh fixed` → all three names, `started 3 of 3`, exit 0. The worker's input is redirected from `/dev/null`.

Starting every worker is not proof that every job completed, so completion is checked separately:

`python3 labs.py coverage` → missing `demo-b`, `demo-c`; `pass: false`; exit 2.
`python3 labs.py coverage --fixed` → three recorded items, none missing or failed, one skipped with a reason; `pass: true`; exit 0.

The check also rejects duplicate records, unexpected items and skips without a reason (see `test_labs.py`). Pass: the short run fails, the fixed loop starts all three, and the completion check rejects missing or duplicate records.
