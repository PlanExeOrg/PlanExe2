You verify a table of canonical facts for a project plan before any later document is written from
it. The facts must be internally consistent: totals equal the sum of their parts, derived numbers follow
from the arithmetic shown in `basis` (recompute every product, sum, ratio, annuity and percentage),
contingency or reserve amounts are not counted twice (e.g. a reserve that sits inside the contingency
reduces the free contingency), units and counts agree with capacities and budgets, and dates/months are
in a feasible order.

Return the complete corrected table in the same format: keep correct facts unchanged, fix wrong values
and their `basis`, and add a fact where a missing one is needed to close a gap (e.g. free contingency
after reserves). If two facts conflict and the documents do not settle which is right, keep the more
defensible one and say in `basis` that a decision is needed. Summarize your corrections in
`reconciliation_notes`.
