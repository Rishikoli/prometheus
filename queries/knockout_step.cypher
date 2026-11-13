// params: {"y": 2005, "loss": "ZERO_MAP"}
// One round of the knock-out cascade: every field takes the average exposure of the fields it builds on.
// $loss is a map from field code to its current exposure (the removed field is pinned at 1).
// exposure(next) = gamma * sum(link * exposure of prerequisite) / sum(link); the code applies gamma and repeats.
MATCH (f:Field)-[r:BUILDS_ON]->(p:Field)
WHERE r.firstYear <= $y
RETURN f.code AS field, sum($loss[p.code]) AS weightedExposure, count(r) AS links
ORDER BY field
