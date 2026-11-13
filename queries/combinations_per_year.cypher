// params: {}
// How many new combinations appeared each year (the growth curve of the graph).
MATCH ()-[r:COMBINED_WITH]->()
RETURN r.firstYear AS year, count(r) AS newCombinations
ORDER BY year
