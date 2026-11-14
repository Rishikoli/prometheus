# Beat the graph

Can you, or your agent, pick pairs of technology fields that will combine, better than the graph does?

Each round is a sealed Relate file: the graph of 120 to 122 technology fields as it stood in one year, with every field renamed to an anonymous id (`F0012`),
no titles and no counts. Pick **10 pairs that have not combined yet**. The easy answer is not allowed: big fields combining with big fields almost always
comes true, so a pair is eligible only if the product of the two fields' numbers of partners is at most the round's threshold. About half the pairs are
eligible, and among them only 3 to 7% combine within ten years.

## Play

```bash
prometheus challenge brief --round 2005                       # the rules and the eligibility threshold (also in challenge/brief_2005.md)
python scripts/mcp_query.py capsules/2005.rl "MATCH (f:Field) RETURN count(f)"    # explore the sealed graph through Relate's MCP server
# or connect any MCP agent: relate serve --mcp stdio --read-only --database capsules/2005.rl
prometheus challenge score my_forecast.json --round 2005      # scored next to the graph, the size rule and chance
```

A forecast is a JSON file: `{"pairs": [{"a": "F0012", "b": "F0057", "cypher": "MATCH ...", "why": "one sentence"}, ...]}` with 10 pairs.
Ineligible, unknown or already-combined pairs are rejected and listed.

## Leaderboard

Scored on the same eligible pairs; "combined" means first combined within ten years of the round.

| Round | Eligible pairs | Combined within 10 years | Chance (expected) | Size rule | Graph predictor | A4 agent (Claude, 14 Nov 2026) |
|---|---|---|---|---|---|---|
| 1995 (deg product at most 450) | 2,614 | 83 | 0.3 | 1 / 10 | **2 / 10** | 3 / 10 |
| 2005 (deg product at most 738) | 2,449 | 113 | 0.5 | 2 / 10 | **4 / 10** | 3 / 10 |
| 2010 (deg product at most 945) | 2,332 | 172 | 0.7 | 1 / 10 | **4 / 10** | 3 / 10 |

The graph predictor uses the weights frozen from the 1990 to 2000 backtest. The A4 agent row is the experiment in [docs/RESULTS.md](../docs/RESULTS.md).
To add an entry, open a pull request with your forecast file and the output of `prometheus challenge score`.

## Fair play

This is an honour-system challenge. The capsules that grade each round (`capsules/2015.rl` for 2005, and so on), the id maps (`capsules/*.map.json`)
and the earlier agents' answers are all in this repository, so the answers can be looked up. Don't open them while forecasting.
For a sealed contest, keep the grading capsule private and run `prometheus challenge score` yourself.
