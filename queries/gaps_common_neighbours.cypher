// params: {"y": 2000}
// The adjacent possible: pairs of fields that have NOT combined as of year $y, ranked by how many
// fields are already combined with both (common neighbours). Time-aware on every edge.
MATCH (a:Field)-[r1:COMBINED_WITH]-(n:Field)-[r2:COMBINED_WITH]-(b:Field)
WHERE a.code < b.code
  AND r1.firstYear <= $y AND r2.firstYear <= $y
  AND NOT EXISTS { MATCH (a)-[x:COMBINED_WITH]-(b) WHERE x.firstYear <= $y }
RETURN a.code AS a, b.code AS b, count(DISTINCT n) AS commonNeighbours
ORDER BY commonNeighbours DESC, a, b
