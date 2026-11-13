// params: {"y": 2000}
// How many partners each field had as of year $y (used by Adamic-Adar and preferential attachment).
MATCH (n:Field)-[r:COMBINED_WITH]-()
WHERE r.firstYear <= $y
RETURN n.code AS code, count(r) AS degree
ORDER BY degree DESC, code
