# Forecaster brief

You are forecasting which pairs of technology fields will first be combined in a patent
family during the next 10 years (after 2005).

You may use ONLY the read-only database tools of the `capsule-2005` MCP server. The database is
a snapshot of everything known up to 2005:

- `(:Field {code, firstYear})` - an anonymous technology field; `firstYear` is when it began.
- `(:Field)-[:COMBINED_WITH {firstYear}]-(:Field)` - two fields already combined, since that year.
- `(:Field)-[:BUILDS_ON {firstYear}]->(:Field)` - the first field cites the second as a prerequisite.

Field names are hidden on purpose. Do not try to guess what the fields are.

Eligibility rule (this run only). Let deg(X) be the number of fields X is already combined with
(`COMBINED_WITH`, in either direction). A pair (a, b) is eligible ONLY if

    deg(a) * deg(b) <= 738

Pairs above that value are the well-known big-field-meets-big-field pairs and are NOT eligible. All
10 of your pairs must be eligible and must not already be connected by COMBINED_WITH. Check each
pair's eligibility with a query before you include it.

Task: return the 10 pairs of fields you think are most likely to combine for the first time
after 2005. Pairs must not already be connected by COMBINED_WITH. For each pair, include
the exact Cypher query that produced or supports it. Reply with JSON only:

{"pairs": [{"a": "F0001", "b": "F0002", "cypher": "MATCH ...", "why": "one sentence"}]}
