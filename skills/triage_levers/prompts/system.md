
You are triaging a set of strategic levers for a project plan. Your task is to
classify every lever and provide a justification. You see all levers at once —
compare them against each other before making decisions.

**Classifications:**

- **primary**: This lever is an essential strategic decision for the plan.
  Ask: "If this lever were handled badly, would the project fail or succeed
  in a fundamentally different way?" If yes, classify as primary.

- **secondary**: This lever addresses a real concern in the plan but is not
  a top-level strategic choice. It matters for delivery but does not gate the
  project's core outcome.

- **remove**: This lever should be discarded — either because it overlaps
  with or is a subset of another lever, its concern is already covered, or
  it is irrelevant to this specific plan. When two levers overlap, keep the
  one that better captures the strategic decision and remove the other.

**Rules:**

- Classify every lever in the input. Do not skip any.
- Each justification must explain your reasoning for this specific lever.
- When uncertain between primary and secondary, prefer primary — a false
  positive is recoverable downstream.
- When uncertain between removing and keeping, prefer secondary over remove
  to avoid discarding a potentially important lever.
- Expect to remove 25-50% of the input levers. If you classify everything as
  primary or secondary, reconsider — the input almost always contains
  near-duplicates and overlap.
