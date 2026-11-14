"""Call a Relate MCP server over HTTP (`relate serve --mcp PORT`), for agents or scripts without an MCP client.

    python scripts/mcp_http.py --port 8799 --token-file results/ledger/ledger.rl.auth-token read  "MATCH (n) RETURN count(n)"
    python scripts/mcp_http.py --port 8799 --token-file results/ledger/ledger.rl.auth-token write "MERGE ..." --params '{"agent": "a1"}'

`relate serve` writes its access token next to the store as `<store>.auth-token` (`user:token`). Each `write` is one
statement, which Relate runs as one transaction.
"""
import argparse
import base64
import json
import sys
import urllib.request


def call(port, token_file, tool, args):
    auth = "Basic " + base64.b64encode(open(token_file).read().strip().encode()).decode()
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                                          "Authorization": auth})
    text = urllib.request.urlopen(req, timeout=60).read().decode()
    if "data:" in text[:200]:
        text = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")][-1]
    return json.loads(text)["result"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--token-file", required=True)
    ap.add_argument("mode", choices=["read", "write", "schema"])
    ap.add_argument("statement", nargs="?", default="")
    ap.add_argument("--params", default="{}", help="JSON object of statement parameters")
    ap.add_argument("--statement-file", help="read the statement from a file (easier than quoting a multi-line statement)")
    ap.add_argument("--params-file", help="read the parameters (a JSON object) from a file")
    a = ap.parse_args(argv)
    if a.statement_file:
        a.statement = open(a.statement_file).read()
    if a.params_file:
        a.params = open(a.params_file).read()
    if a.mode == "schema":
        res = call(a.port, a.token_file, "get_schema", {})
    else:
        res = call(a.port, a.token_file, "read_cypher" if a.mode == "read" else "write_cypher",
                   {"statement": a.statement, "parameters": json.loads(a.params)})
    text = res["content"][0]["text"]
    if res.get("isError"):
        print("ERROR:", text)
        return 1
    try:
        data = json.loads(text)
        print(json.dumps(data.get("rows", data), indent=1))
    except json.JSONDecodeError:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
