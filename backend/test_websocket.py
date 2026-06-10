"""WebSocket integration test for Phase 7.

Connects to the running FastAPI server, sends a research task, and
prints every streaming chunk received.

Prerequisites — start the server first in another terminal:
    .\\venv\\Scripts\\python.exe -m uvicorn api.main:api --reload --port 8000

Then run this script:
    .\\venv\\Scripts\\python.exe test_websocket.py
"""

import asyncio
import json

try:
    import websockets
except ImportError:
    raise SystemExit("websockets not installed. Run: pip install websockets")

WS_URL    = "ws://localhost:8000/ws/chat"
TEST_MSG  = "What is RAG in AI systems?"
SESSION   = "test-ws-001"


async def run_test():
    print("=" * 60)
    print("Atlas — WebSocket Integration Test")
    print("=" * 60)
    print(f"Connecting to: {WS_URL}")
    print(f"Sending task : {TEST_MSG!r}")
    print("-" * 60)

    chunks_received = 0
    content_received = False

    try:
        async with websockets.connect(WS_URL) as ws:
            # Send the task
            payload = {"message": TEST_MSG, "session_id": SESSION}
            await ws.send(json.dumps(payload))
            print("Message sent. Waiting for agent response...\n")

            # Receive chunks until done
            while True:
                raw = await ws.recv()
                chunk = json.loads(raw)

                if chunk.get("error"):
                    print(f"  ERROR from server: {chunk['error']}")
                    break

                if chunk.get("done"):
                    print("\n[Stream complete]")
                    break

                chunks_received += 1
                agent   = chunk.get("agent", "unknown")
                content = chunk.get("content", "")

                # Parse and preview content
                try:
                    parsed = json.loads(content) if content else {}
                    # Find the first non-empty value in results dict
                    preview = ""
                    for v in parsed.values():
                        if v:
                            preview = str(v)[:200]
                            content_received = True
                            break
                except Exception:
                    preview = content[:200]
                    if preview:
                        content_received = True

                print(f"  Chunk {chunks_received}: agent={agent!r}")
                if preview:
                    print(f"  Content preview : {preview}{'...' if len(str(preview)) >= 200 else ''}")

    except ConnectionRefusedError:
        print("ERROR: Could not connect to ws://localhost:8000/ws/chat")
        print("Is the server running? Start it with:")
        print("  .\\venv\\Scripts\\python.exe -m uvicorn api.main:api --reload --port 8000")
        return

    # Verdict
    print("\n" + "=" * 60)
    if chunks_received > 0 and content_received:
        print(f"PASS -- received {chunks_received} chunk(s) with content")
    elif chunks_received > 0:
        print(f"PARTIAL -- received {chunks_received} chunk(s) but no content preview parsed")
    else:
        print("FAIL -- no chunks received")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test())
