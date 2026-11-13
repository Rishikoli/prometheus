// params: {"a": "TOY050", "b": "TOY090", "y": 2005}
// Bridge fields for a gap: fields already combined with BOTH sides, as of year $y. Ranked in code by how
// long the newer of the two links has existed. (Example parameters are for the toy store; use real CPC codes.)
MATCH (a:Field {code: $a})-[r1:COMBINED_WITH]-(c:Field)-[r2:COMBINED_WITH]-(b:Field {code: $b})
WHERE r1.firstYear <= $y AND r2.firstYear <= $y
RETURN c.code AS bridge, c.title AS title, r1.firstYear AS linkToA, r2.firstYear AS linkToB
ORDER BY bridge
