// params: {"a": "TOY050", "b": "TOY090", "y": 2005}
// Fields that both $a and $b build on, as of year $y.
MATCH (a:Field {code: $a})-[r1:BUILDS_ON]->(c:Field)<-[r2:BUILDS_ON]-(b:Field {code: $b})
WHERE r1.firstYear <= $y AND r2.firstYear <= $y
RETURN c.code AS prerequisite, c.title AS title, c.firstYear AS since
ORDER BY prerequisite
