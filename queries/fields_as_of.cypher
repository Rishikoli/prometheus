// params: {"y": 2000}
// Time travel: the fields that exist as of year $y. Every snapshot of history is a filter on firstYear.
MATCH (f:Field)
WHERE f.firstYear <= $y
RETURN f.code AS code, f.title AS title, f.firstYear AS firstYear
ORDER BY code
