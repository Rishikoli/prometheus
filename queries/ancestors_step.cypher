// params: {"fr": ["TOY100"], "y": 2005}
// One level of ancestry: the fields the frontier builds on. The code calls this once per level, which keeps
// the cost proportional to the number of edges (one variable-length path query enumerates every path).
MATCH (f:Field)-[r:BUILDS_ON]->(p:Field)
WHERE f.code IN $fr AND r.firstYear <= $y
RETURN DISTINCT p.code AS ancestor
ORDER BY ancestor
