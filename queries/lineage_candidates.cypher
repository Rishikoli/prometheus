// params: {}
// Candidate parents for the lineage tree: strictly older prerequisites. The code keeps, for each field,
// the one with the largest link count (then the oldest, then by code), so every field hangs from one parent.
MATCH (f:Field)-[r:BUILDS_ON]->(p:Field)
WHERE p.firstYear < f.firstYear
RETURN f.code AS child, p.code AS parent, r.count AS links, p.firstYear AS parentSince
ORDER BY child, links DESC, parentSince, parent
