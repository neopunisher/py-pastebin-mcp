#!/usr/bin/env python3
"""Smoke-test a built wheel by speaking MCP to its console script over stdio.

Installs the wheel into an ephemeral ``uvx`` environment, runs the packaged
``mcp-pastebin`` entry point, and checks that it answers a JSON-RPC
``initialize`` request and reports its tools. Exits non-zero on any failure.

Usage: python scripts/smoke_test.py [dist/*.whl glob]
"""

from __future__ import annotations

import glob
import json
import os
import queue
import subprocess
import sys
import threading
import time

PROTOCOL_VERSION = "2025-06-18"
# uvx resolves and downloads the dependency tree on a cold cache.
TIMEOUT = 180.0


def fail(message: str, stderr: list[str] | None = None) -> None:
    print(f"smoke test FAILED: {message}", file=sys.stderr)
    if stderr:
        print("--- server stderr ---", file=sys.stderr)
        sys.stderr.write("".join(stderr[-40:]))
    raise SystemExit(1)


def find_wheel(pattern: str) -> str:
    wheels = sorted(glob.glob(pattern))
    if not wheels:
        fail(f"no wheel matched {pattern!r} - run `uv build` first")
    if len(wheels) > 1:
        fail(f"{len(wheels)} wheels matched {pattern!r} - clean dist/ and rebuild")
    return wheels[0]


def pump(stream, sink) -> None:
    for line in stream:
        sink(line)
    sink(None)


def read_reply(replies: queue.Queue, want_id: int, deadline: float, stderr: list[str]) -> dict:
    """Return the JSON-RPC message with ``want_id``, skipping non-JSON output."""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail(f"timed out waiting for a reply to request id {want_id}", stderr)
        try:
            line = replies.get(timeout=remaining)
        except queue.Empty:
            fail(f"timed out waiting for a reply to request id {want_id}", stderr)
        if line is None:
            fail("server closed stdout before replying", stderr)
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue  # banners and log lines are not our problem
        if isinstance(message, dict) and message.get("id") == want_id:
            return message


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "*.whl")
    wheel = find_wheel(pattern)
    command = ["uvx", "--from", wheel, "mcp-pastebin"]
    print(f"$ {' '.join(command)}")

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    replies: queue.Queue = queue.Queue()
    stderr: list[str] = []
    threading.Thread(target=pump, args=(process.stdout, replies.put), daemon=True).start()
    threading.Thread(
        target=pump,
        args=(process.stderr, lambda line: stderr.append(line) if line else None),
        daemon=True,
    ).start()

    deadline = time.monotonic() + TIMEOUT

    def send(message: dict) -> None:
        try:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()
        except BrokenPipeError:
            fail("server exited before it could be asked anything", stderr)

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "smoke-test", "version": "0"},
                },
            }
        )
        reply = read_reply(replies, 1, deadline, stderr)
        if "error" in reply:
            fail(f"initialize returned an error: {reply['error']}", stderr)
        result = reply.get("result") or {}
        server = result.get("serverInfo") or {}
        if not result.get("protocolVersion") or not server.get("name"):
            fail(f"initialize result is missing serverInfo/protocolVersion: {reply}", stderr)
        print(
            f"initialize ok: {server.get('name')} {server.get('version', '?')} "
            f"(protocol {result['protocolVersion']})"
        )

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        reply = read_reply(replies, 2, deadline, stderr)
        if "error" in reply:
            fail(f"tools/list returned an error: {reply['error']}", stderr)
        tools = (reply.get("result") or {}).get("tools") or []
        if not tools:
            fail(f"tools/list returned no tools: {reply}", stderr)
        print(f"tools/list ok: {', '.join(tool['name'] for tool in tools)}")
    finally:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()

    print("smoke test passed")


if __name__ == "__main__":
    main()
