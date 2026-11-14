"""Run read-only Cypher against a Relate store through Relate's own MCP server (`relate serve --mcp stdio --read-only`).

    python scripts/mcp_query.py STORE "MATCH ..." ["MATCH ..." ...]     # prints each query's rows as JSON
    python scripts/mcp_query.py STORE --check agent/PROMPT.md          # runs every ```cypher block in a file; non-zero exit if any fails

It is a minimal MCP client: the same protocol and tools an agent gets (get_schema, read_cypher). Needs the `relate` CLI on PATH.
"""
import json
import re
import shutil
import subprocess
import sys


def session(store):
    exe = shutil.which("relate") or "relate"
    p = subprocess.Popen([exe, "serve", "--mcp", "stdio", "--database", store, "--read-only"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    n = [0]

    def rpc(method, params=None):
        n[0] += 1
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n[0], "method": method, "params": params or {}}) + "\n")
        p.stdin.flush()
        return json.loads(p.stdout.readline())

    rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "mcp_query", "version": "1"}})
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    p.stdin.flush()

    def run(statement):
        r = rpc("tools/call", {"name": "read_cypher", "arguments": {"statement": statement}})["result"]
        text = r["content"][0]["text"]
        if r.get("isError"):
            raise RuntimeError(text)
        return json.loads(text)["rows"]
    return p, run


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    store, rest = argv[0], argv[1:]
    p, run = session(store)
    try:
        if rest[0] == "--check":
            blocks = re.findall(r"```cypher\n(.*?)```", open(rest[1]).read(), re.S)
            bad = 0
            for b in blocks:
                try:
                    rows = run(b.strip())
                    print(f"ok    {len(rows):>3} rows  {b.strip()[:90]}")
                except RuntimeError as e:
                    bad += 1
                    print(f"FAIL  {b.strip()[:90]}\n      {e}")
            print(f"{len(blocks)} queries, {bad} failed")
            return 1 if bad else 0
        for q in rest:
            print(json.dumps(run(q), indent=1))
        return 0
    finally:
        p.stdin.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
