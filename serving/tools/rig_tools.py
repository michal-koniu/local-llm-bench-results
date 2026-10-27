#!/usr/bin/env python3
"""rig-tools: tools for the local models on this rig, as an MCP server.

Gives a model the local shell, files and the public internet:
  run_command, read_file, write_file, edit_file, list_directory   (local, as user mkoniu)
  web_search, fetch_url                                            (internet)

Two ways to run it:
  --http   streamable HTTP on --host/--port at /mcp, bearer token from --token-file.
           Used by Open WebUI (all models). systemd unit: rig-tools.service.
  --stdio  over stdin/stdout, started by llama-server (--mcp-servers-config).
           With --web-only it offers just web_search and fetch_url, because
           llama-server already has its own shell and file tools (--tools all).

Every overwrite or edit first copies the old file to ~/.cache/rig-tools/backups/.
"""
import argparse, datetime, os, pathlib, shutil, subprocess

from mcp.server.fastmcp import FastMCP

HOME = pathlib.Path.home()
BACKUPS = HOME / ".cache" / "rig-tools" / "backups"
MAX_OUT = 30000


def _clip(text: str, limit: int = MAX_OUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [cut: {len(text) - limit} more characters]"


def _path(p: str) -> pathlib.Path:
    return pathlib.Path(os.path.expanduser(p)).resolve()


def _backup(p: pathlib.Path) -> str:
    if not p.is_file():
        return ""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BACKUPS / (str(p).lstrip("/").replace("/", "__") + "." + stamp)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dst)
    return str(dst)


def add_local_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def run_command(command: str, workdir: str = "~", timeout_seconds: int = 300) -> str:
        """Run a bash command on the rig (Ubuntu, user mkoniu, internet access, no sudo password).
        Returns the exit code and the combined stdout/stderr (long output is cut)."""
        try:
            r = subprocess.run(["bash", "-lc", command], cwd=_path(workdir), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               timeout=timeout_seconds)
            return f"exit code {r.returncode}\n" + _clip(r.stdout)
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            return f"timed out after {timeout_seconds}s\n" + _clip(out)

    @mcp.tool()
    def read_file(path: str, start_line: int = 1, max_lines: int = 500) -> str:
        """Read a text file, with line numbers. Use start_line/max_lines for long files."""
        p = _path(path)
        lines = p.read_text(errors="replace").splitlines()
        part = lines[start_line - 1:start_line - 1 + max_lines]
        body = "\n".join(f"{i}\t{l}" for i, l in enumerate(part, start_line))
        return f"{p} ({len(lines)} lines)\n" + _clip(body)

    @mcp.tool()
    def write_file(path: str, content: str, append: bool = False) -> str:
        """Create or overwrite a file (or append to it). The old version is backed up first."""
        p = _path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        bak = "" if append else _backup(p)
        with open(p, "a" if append else "w") as f:
            f.write(content)
        return f"wrote {len(content.encode())} bytes to {p}" + (f"; backup of the old file: {bak}" if bak else "")

    @mcp.tool()
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace old_text (must occur exactly once) with new_text in a file. The old version is backed up first."""
        p = _path(path)
        s = p.read_text()
        n = s.count(old_text)
        if n != 1:
            return f"not changed: old_text occurs {n} times in {p} (must be exactly once)"
        bak = _backup(p)
        p.write_text(s.replace(old_text, new_text))
        return f"edited {p}; backup of the old file: {bak}"

    @mcp.tool()
    def list_directory(path: str = "~") -> str:
        """List a directory: type, size and name of each entry."""
        p = _path(path)
        rows = []
        for e in sorted(p.iterdir(), key=lambda e: e.name):
            kind = "dir " if e.is_dir() else "file"
            size = e.stat().st_size if e.is_file() else ""
            rows.append(f"{kind} {size:>12} {e.name}")
        return f"{p}\n" + _clip("\n".join(rows))


def add_web_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def web_search(query: str, max_results: int = 8) -> str:
        """Search the public web. Returns title, URL and snippet per result."""
        from ddgs import DDGS
        errors = []
        for backend in ("auto", "duckduckgo", "bing", "brave", "mojeek"):   # engines rate-limit now and then
            try:
                res = DDGS().text(query, max_results=max_results, backend=backend)
            except Exception as e:
                errors.append(f"{backend}: {e}")
                continue
            if res:
                return "\n\n".join(f"{r.get('title')}\n{r.get('href')}\n{r.get('body')}" for r in res)
        return "no results (" + "; ".join(errors) + ")"

    @mcp.tool()
    def fetch_url(url: str, max_chars: int = 20000) -> str:
        """Download a public web page or file and return its readable text (HTML is converted to markdown)."""
        import httpx, trafilatura
        r = httpx.get(url, follow_redirects=True, timeout=30,
                      headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) rig-tools"})
        ctype = r.headers.get("content-type", "")
        text = r.text
        if "html" in ctype:
            text = trafilatura.extract(r.text, output_format="markdown", include_links=True) or r.text
        return f"HTTP {r.status_code} {r.url} ({ctype})\n\n" + _clip(text, max_chars)


INSTRUCTIONS = ("Tools on the user's local AI rig: local shell and files as user mkoniu, "
                "plus web search and page fetching on the public internet.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", action="store_true")
    ap.add_argument("--stdio", action="store_true")
    ap.add_argument("--web-only", action="store_true")
    ap.add_argument("--host", default="172.17.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token-file", default=str(HOME / ".config" / "rig-tools" / "token"))
    a = ap.parse_args()

    # host other than localhost: FastMCP does not add DNS-rebinding checks; the bearer token protects it
    mcp = FastMCP("rig-tools", instructions=INSTRUCTIONS, host=a.host, port=a.port, stateless_http=True)
    if not a.web_only:
        add_local_tools(mcp)
    add_web_tools(mcp)

    if a.stdio:
        mcp.run(transport="stdio")
        return

    import uvicorn
    token = pathlib.Path(a.token_file).read_text().strip()
    app = mcp.streamable_http_app()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            auth = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
            if auth != f"Bearer {token}":
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await app(scope, receive, send)

    uvicorn.run(guarded, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
