# Source/version ledger

| Version | Full release gate | Source |
|---|---|---|
| v1 | Six cases + Base + seed extension passed; original snapshot | [entry](v1/main/solve.py) |
| v2 | STOP: large4 process killed after60s; 5 prior runs passed | [candidate](v2/main/solve.py) |
| v2.1, presolve off | STOP: large4 process killed after60s; 5 prior runs passed | [candidate](v2_1/main/solve.py) |
| **v3, current** | **9/9 complete runs PASS** | [entry](v3/main/solve.py) |

Current `main/solve.py` and v3 archive are byte-identical. v1's complete original
repo replay is also fixed at commit `45a576cf0d6df9cc0ed935f93c5c1e8040e70d59`.
All earlier sources, candidate failures and measured solutions remain distinct.
