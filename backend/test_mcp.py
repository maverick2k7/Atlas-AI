"""Verify Gmail + Calendar MCP connections.

Run from backend/ (after auth_setup.py):
    .\\venv\\Scripts\\python.exe test_mcp.py
"""

import asyncio
import sys

from mcp_servers.client import get_mcp_client, is_mcp_configured


async def test() -> None:
    if not is_mcp_configured():
        print("FAIL: token.json not found.")
        print("Run: python backend/credentials/auth_setup.py")
        sys.exit(1)

    print("Connecting to MCP servers...")

    client = get_mcp_client()

    gmail_tools = await client.get_tools(server_name="gmail")
    print(f"\nGmail tools ({len(gmail_tools)} found):")
    for t in gmail_tools:
        print(f"   - {t.name}")

    calendar_tools = await client.get_tools(server_name="google_calendar")
    print(f"\nGoogle Calendar tools ({len(calendar_tools)} found):")
    for t in calendar_tools:
        print(f"   - {t.name}")

    if not gmail_tools or not calendar_tools:
        print("\nFAIL: One or both servers returned no tools.")
        sys.exit(1)

    print("\nMCP setup complete. Both servers are connected.")


if __name__ == "__main__":
    asyncio.run(test())
