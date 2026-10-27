#!/usr/bin/env python3
"""
llama-pool.py — run ONE model as N independent llama-server copies (one per GPU) behind ONE port.

WHY
  A model that fits on a single card (e.g. Qwen3.6-35B-A3B, ~21 GiB) gains nothing from being split
  across 4 cards: with layer split the cards work one after another, so 4 cards decode about as fast
  as 1. Four separate copies, one per card, decode four times as many tokens per second in total.
  Each copy also serves several agents at once (--parallel), so 4 copies x 3 slots = 12 agents.

  Clients (OpenClaw, opencode, any OpenAI-compatible harness) should not have to know there are four
  servers. This script is the single endpoint: llama-swap starts it like any other model and gives
  it ${PORT}; it starts the copies on 127.0.0.1:BASE_PORT+i and forwards every request to one of them.

ROUTING (why not plain round-robin)
  llama-server keeps each conversation's KV cache in the slot that served it. The next turn of the
  same conversation only has to read the NEW tokens if it lands on the same server — otherwise the
  whole history (often 20-60k tokens) is read again, which costs 10-30 s per turn. So:
    1. A conversation is identified by a hash of its first two messages (system prompt + first user
       message); these never change between turns.
    2. A known conversation goes back to the server that already has it cached, if that server has a
       free slot and is not already working on the same conversation.
    3. Anything else goes to the server with the fewest requests in flight.

USAGE (normally from llama-swap's config.yaml)
  llama-pool.py --port ${PORT} --gpus 0,1,2,3 --slots 3 --server /path/llama-server -- <llama-server args>

  Everything after "--" is passed to every copy; the script adds --host, --port and --parallel itself
  and limits every copy to one GPU (HIP_/CUDA_/GGML_VK_VISIBLE_DEVICES, so ROCm, CUDA and Vulkan builds all work).

  GET /health        200 only when every copy is healthy (llama-swap waits for this)
  GET /pool          JSON: per-copy requests in flight, requests served, conversations remembered
  anything else      forwarded to a copy (POST by the rules above, GET to the first copy)

Standard library only. License: MIT
"""
import argparse, asyncio, ctypes, hashlib, json, os, signal, sys, time
from collections import OrderedDict

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, required=True, help="port clients (llama-swap) talk to")
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--gpus", default="0,1,2,3", help="one llama-server copy per listed GPU index")
ap.add_argument("--slots", type=int, default=3, help="--parallel for every copy (agents per GPU)")
ap.add_argument("--base-port", type=int, default=18100, help="copies listen on base-port+0..N-1")
ap.add_argument("--server", default=os.path.expanduser("~/llama.cpp/build/bin/llama-server"))
ap.add_argument("server_args", nargs=argparse.REMAINDER)
A = ap.parse_args()
SERVER_ARGS = [a for a in A.server_args if a != "--"]
GPUS = [g.strip() for g in A.gpus.split(",") if g.strip()]


class Backend:
    def __init__(self, i, gpu):
        self.i, self.gpu, self.port = i, gpu, A.base_port + i
        self.inflight, self.served, self.keys_now = 0, 0, {}
        self.proc = None

    def full(self):
        return self.inflight >= A.slots


BACK = [Backend(i, g) for i, g in enumerate(GPUS)]
AFFINITY = OrderedDict()          # conversation key -> set of backend indices that have it cached
AFFINITY_MAX = 4096


def log(*a):
    print("[pool]", *a, flush=True)


def conv_key(body):
    try:
        j = json.loads(body)
    except Exception:
        return None
    msgs = j.get("messages")
    if isinstance(msgs, list) and msgs:
        head = msgs[:2]
    elif "prompt" in j:
        head = str(j["prompt"])[:4000]
    else:
        return None
    return hashlib.sha1(json.dumps(head, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def pick(key):
    cands = []
    if key and key in AFFINITY:
        AFFINITY.move_to_end(key)
        cands = [BACK[i] for i in AFFINITY[key] if not BACK[i].full() and not BACK[i].keys_now.get(key)]
    if not cands:
        cands = BACK
    b = min(cands, key=lambda x: (x.inflight, x.served))
    if key:
        AFFINITY.setdefault(key, set()).add(b.i)
        while len(AFFINITY) > AFFINITY_MAX:
            AFFINITY.popitem(last=False)
    return b


# ---------------------------------------------------------------- HTTP plumbing
async def read_request(reader):
    head = await reader.readuntil(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    method, path, _ = lines[0].split(" ", 2)
    headers = []
    for ln in lines[1:]:
        if ln:
            k, v = ln.split(":", 1)
            headers.append((k.strip(), v.strip()))
    hl = {k.lower(): v for k, v in headers}
    body = b""
    if "content-length" in hl:
        body = await reader.readexactly(int(hl["content-length"]))
    elif hl.get("transfer-encoding", "").lower() == "chunked":
        while True:
            size = int((await reader.readline()).split(b";")[0].strip(), 16)
            if size == 0:
                await reader.readline()
                break
            body += await reader.readexactly(size)
            await reader.readline()
    return method, path, headers, body


async def forward(b, method, path, headers, body, cw):
    """Send the request to backend b and pipe its raw response to the client until EOF."""
    r, w = await asyncio.open_connection("127.0.0.1", b.port)
    drop = {"host", "connection", "content-length", "transfer-encoding", "keep-alive"}
    out = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{b.port}", "Connection: close",
           f"Content-Length: {len(body)}"] + [f"{k}: {v}" for k, v in headers if k.lower() not in drop]
    w.write(("\r\n".join(out) + "\r\n\r\n").encode("latin-1") + body)
    await w.drain()
    try:
        while True:
            chunk = await r.read(65536)
            if not chunk:
                break
            cw.write(chunk)
            await cw.drain()
    finally:
        w.close()


def respond(cw, code, obj):
    data = json.dumps(obj, indent=1).encode()
    cw.write(f"HTTP/1.1 {code} {'OK' if code == 200 else 'Service Unavailable'}\r\nContent-Type: application/json\r\n"
             f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data)


async def healthy(b):
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", b.port), 2)
        w.write(b"GET /health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        await w.drain()
        line = await asyncio.wait_for(r.readline(), 5)
        w.close()
        return b" 200 " in line
    except Exception:
        return False


async def handle(cr, cw):
    try:
        method, path, headers, body = await read_request(cr)
        if path.startswith("/health"):
            ok = all(await asyncio.gather(*(healthy(b) for b in BACK)))
            respond(cw, 200 if ok else 503, {"status": "ok" if ok else "loading", "copies": len(BACK)})
        elif path.startswith("/pool"):
            respond(cw, 200, {"slots_per_copy": A.slots, "conversations_remembered": len(AFFINITY),
                              "copies": [dict(gpu=b.gpu, port=b.port, inflight=b.inflight, served=b.served)
                                         for b in BACK]})
        elif method == "POST":
            key = conv_key(body)
            b = pick(key)
            b.inflight += 1
            if key:
                b.keys_now[key] = b.keys_now.get(key, 0) + 1
            try:
                await forward(b, method, path, headers, body, cw)
            finally:
                b.inflight -= 1
                b.served += 1
                if key:
                    b.keys_now[key] -= 1
                    if not b.keys_now[key]:
                        del b.keys_now[key]
        else:
            await forward(BACK[0], method, path, headers, body, cw)
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    except Exception as e:
        log("request error:", repr(e))
    finally:
        try:
            await cw.drain()
            cw.close()
        except Exception:
            pass


# ---------------------------------------------------------------- process management
def die_with_parent():
    # if this script is SIGKILLed, the kernel sends SIGTERM to every copy, so no orphan keeps VRAM busy
    ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)


async def pump(b):
    async for line in b.proc.stdout:
        sys.stdout.write(f"[gpu{b.gpu}] " + line.decode(errors="replace"))
        sys.stdout.flush()


async def start(b):
    env = dict(os.environ, HIP_VISIBLE_DEVICES=b.gpu, CUDA_VISIBLE_DEVICES=b.gpu, GGML_VK_VISIBLE_DEVICES=b.gpu)
    cmd = [A.server, "--host", "127.0.0.1", "--port", str(b.port), "--parallel", str(A.slots)] + SERVER_ARGS
    log(f"gpu {b.gpu}: {' '.join(cmd)}")
    b.proc = await asyncio.create_subprocess_exec(*cmd, env=env, stdout=asyncio.subprocess.PIPE,
                                                  stderr=asyncio.subprocess.STDOUT, preexec_fn=die_with_parent)
    asyncio.create_task(pump(b))


async def main():
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(s, stop.set)
    for b in BACK:
        await start(b)
    srv = await asyncio.start_server(handle, A.host, A.port, limit=1 << 24)
    log(f"listening on {A.host}:{A.port}, {len(BACK)} copies x {A.slots} slots = {len(BACK) * A.slots} agents")
    died = asyncio.ensure_future(asyncio.wait([asyncio.ensure_future(b.proc.wait()) for b in BACK],
                                              return_when=asyncio.FIRST_COMPLETED))
    await asyncio.wait([asyncio.ensure_future(stop.wait()), died], return_when=asyncio.FIRST_COMPLETED)
    rc = 0
    if not stop.is_set():
        log("a copy exited on its own — stopping the whole pool"); rc = 1
    srv.close()
    for b in BACK:
        if b.proc.returncode is None:
            b.proc.terminate()
    t0 = time.time()
    while time.time() - t0 < 15 and any(b.proc.returncode is None for b in BACK):
        await asyncio.sleep(0.2)
    for b in BACK:
        if b.proc.returncode is None:
            b.proc.kill()
    log("stopped")
    sys.exit(rc)


if __name__ == "__main__":
    asyncio.run(main())
