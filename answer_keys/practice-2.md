# Practice 2 answer key — monthly cost change

Aggregate first (compute has two rows in each month), then compare.

| Service | 2026-10 | 2026-11 | Change |
| --- | ---: | ---: | ---: |
| compute | 100 | 160 | +60 |
| storage | 40 | 45 | +5 |
| network | 10 | 15 | +5 |
| **Total** | **150** | **220** | **+70** |

Percentage change: 70 ÷ 150 × 100 = **46.67%**. Reference: `python3 labs.py costs`.

Manager's note (under 80 words): "Monthly spending increased by USD 70, from USD 150 to USD 220, or 46.67%. Compute contributed USD 60 of the increase. Check compute usage and rates first, then storage and network charges. These totals do not establish whether the increases came from higher usage, price changes or another cause."

Reject causes ("more customers") unless another source supports them. Pass only when all eight rows are included and service changes sum to 70.
