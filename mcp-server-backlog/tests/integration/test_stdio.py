from __future__ import annotations

import asyncio
import os
import sys

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


# テストケース: 実際に子プロセスでstdioサーバーを起動し、tool一覧を取得する。
# 必要な理由: 外部APIへ依存せず、in-memoryテストでは検出できないentry pointとstdio配線を検証するため。
def test_stdio_server_lists_tool() -> None:
    async def scenario() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "backlog_mcp"],
            env={**os.environ, "BACKLOG_BASE_URL": "https://example.backlog.jp"},
        )
        async with Client(stdio_client(parameters)) as client:
            tools = await client.list_tools()

        assert [tool.name for tool in tools.tools] == ["get_issue_context"]

    asyncio.run(scenario())
