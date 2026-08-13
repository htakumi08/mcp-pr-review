from __future__ import annotations

import asyncio
import os
import sys

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


async def probe(backlog_url: str) -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backlog_mcp"],
        env=dict(os.environ),
    )
    async with Client(stdio_client(parameters)) as client:
        result = await client.call_tool(
            "get_issue_context", {"backlog_url": backlog_url}
        )

    if result.is_error or result.structured_content is None:
        raise RuntimeError("MCP get_issue_context failed")
    content = result.structured_content
    retrieval = content["retrieval"]
    relationships = content["relationships"]
    print(f"issue_key={content['issue']['key']}")
    print(f"comments={len(content['comments'])}")
    print(f"change_logs={len(content['change_logs'])}")
    print(f"children={len(relationships['children'])}")
    print(f"related={len(relationships['related'])}")
    print(f"partial={retrieval['partial']}")
    print(f"comments_truncated={retrieval['comments_truncated']}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/probe_mcp.py <backlog-issue-url>")
    asyncio.run(probe(sys.argv[1]))


if __name__ == "__main__":
    main()
