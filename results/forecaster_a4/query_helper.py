"""Read-only Cypher against the capsule in the current folder.
Usage: python3 query.py 'MATCH (f:Field) RETURN count(f) AS n' ['SECOND QUERY' ...]
Prints the result rows as JSON. Writes are refused by the server."""
import glob, json, subprocess, sys
db = glob.glob("*.rl")[0]
p = subprocess.Popen(["relate", "serve", "--mcp", "stdio", "--database", db, "--read-only"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
def rpc(i, m, params=None):
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": m, "params": params or {}}) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
rpc(0, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "forecaster", "version": "0"}})
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); p.stdin.flush()
for i, q in enumerate(sys.argv[1:], 1):
    r = rpc(i, "tools/call", {"name": "read_cypher", "arguments": {"statement": q}})["result"]
    t = r["content"][0]["text"]
    print("ERROR " + t if r.get("isError") else json.dumps(json.loads(t)["rows"], separators=(",", ":"))[:20000])
p.stdin.close()
