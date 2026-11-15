# Forecast ledger demonstration (14 Nov 2026)

A demonstration of agents sharing one Relate graph, declared before it ran (see the git history of `docs/RESULTS.md`). **Not an analysis**; nothing here is pooled with A3 or A4.

## What happened

1. `prometheus ledger init results/ledger/ledger.rl` created an empty ledger.
2. One server held the writer lease: `relate serve --mcp 8799 --database results/ledger/ledger.rl` (HTTP MCP with a generated access token, which is git-ignored).
   A second process opening the same file is refused with "storage locked", which is why every agent writes through the one server.
3. Three fresh Claude subagents ran **at the same time**, each in an isolated folder with a copy of the sealed 2005 capsule (anonymous ids; the id map was not in the folder),
   the brief [agent/LEDGER.md](../../agent/LEDGER.md) and two helpers. Each read the capsule through Relate's read-only MCP server and wrote its ten picks to the ledger
   with **one** `write_cypher` call (the statement in `ledger.RECORD`), which Relate runs as one transaction. Their exact picks are in `picks-agent-*.json`.
4. After the agents finished and the server stopped, `prometheus ledger grade ... --against capsules/2015.rl --as-of 2005` wrote each pair's outcome into the same file.

Audit, from each agent's tool calls: 4, 6 and 4 calls; exactly one ledger write each; nothing read or written outside its folder.
Before this run, a stress test sent 100 writes from four concurrent clients to one server: none was lost, and concurrent `MERGE` on the same agent names created no duplicates.
A statement that fails part-way (division by zero, an invalid property) left nothing behind.

## What is in the ledger

30 forecasts by 3 agents about 17 distinct pairs. Two agents picking the same pair point at the same `Pair` node, so agreement is one query away.

| Agent | Picks | Valid | Combined within 10 years |
|---|---|---|---|
| agent-1 | 10 | 10 | 10 |
| agent-2 | 10 | 10 | 8 |
| agent-3 | 10 | 10 | 10 |

Candidate pairs in 2005: 4,887, of which 660 combined by 2015 (base rate 0.135, so random guessing expects about 1.4 of 10).

Pairs picked by more than one agent:

| Pair | Picked by | Outcome |
|---|---|---|
| F0039 × F0074 | agent-1, agent-2, agent-3 | combined in 2012 |
| F0046 × F0089 | agent-1, agent-2, agent-3 | combined in 2009 |
| F0056 × F0091 | agent-1, agent-2, agent-3 | combined in 2006 |
| F0069 × F0085 | agent-1, agent-2, agent-3 | combined in 2011 |
| F0104 × F0119 | agent-1, agent-2, agent-3 | combined in 2007 |
| F0011 × F0076 | agent-1, agent-3 | combined in 2013 |
| F0025 × F0042 | agent-1, agent-3 | combined in 2006 |
| F0036 × F0054 | agent-2, agent-3 | combined in 2013 |

## How to read it

All three agents ranked by shared combination partners, the size-driven method A3 already found, and in 2005 the top of that ranking is saturated: almost every
pair there combines. So high hit counts here say nothing new about prediction. agent-2's two misses came from a different idea (pairs around the most active recent field).
The point of this run is the mechanism: several agents writing to one graph through Relate, safely, with every pick, its reason, its Cypher and its outcome kept in one file
anyone can open:

```bash
relate --database results/ledger/ledger.rl "MATCH (pr:Pair)<-[:ABOUT]-(f:Forecast)-[:BY]->(a:Agent) RETURN a.name, pr.a, pr.b, pr.outcome, f.why LIMIT 10"
prometheus ledger report results/ledger/ledger.rl --as-of 2005
```
