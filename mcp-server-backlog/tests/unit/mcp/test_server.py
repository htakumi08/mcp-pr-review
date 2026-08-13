from __future__ import annotations

import asyncio

from mcp import Client

from backlog_mcp.mcp.server import build_server


class FakeGetIssueContext:
    async def execute(self, backlog_url: str) -> dict[str, object]:
        if "attacker.example" in backlog_url:
            raise ValueError("Backlog URL origin is not allowed")
        return {
            "issue": {"key": "TEST-1", "summary": "Fetched issue"},
            "comments": [{"id": 1, "content": "requirement"}],
            "change_logs": [],
            "relationships": {"parent": None, "children": [], "related": []},
            "retrieval": {"partial": False, "comments_truncated": False},
        }


# テストケース: MCPがget_issue_contextだけを公開し、backlog_urlを必須入力として宣言する。
# 必要な理由: 意図しないtool公開と、課題キーを利用者へ要求するschemaへの退行を防ぐため。
def test_server_lists_read_only_issue_context_tool() -> None:
    async def scenario() -> None:
        async with Client(build_server(FakeGetIssueContext())) as client:  # type: ignore[arg-type]
            result = await client.list_tools()

        assert [tool.name for tool in result.tools] == ["get_issue_context"]
        tool = result.tools[0]
        assert tool.input_schema["required"] == ["backlog_url"]

    asyncio.run(scenario())


# テストケース: application use caseの実取得結果をMCPのstructured contentとして返す。
# 必要な理由: MCP層が固定値へ退行せず、課題本文・コメントをレビュー側へ渡す契約を守るため。
def test_fetched_issue_context_is_structured() -> None:
    async def scenario() -> None:
        async with Client(build_server(FakeGetIssueContext())) as client:  # type: ignore[arg-type]
            result = await client.call_tool(
                "get_issue_context",
                {"backlog_url": "https://example.backlog.jp/view/TEST-1"},
            )

        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["issue"]["key"] == "TEST-1"
        assert result.structured_content["comments"][0]["content"] == "requirement"

    asyncio.run(scenario())


# テストケース: 設定外hostのBacklog URLをtool errorとして返し、structured contentを生成しない。
# 必要な理由: 信頼できないURLを正常結果として扱い、後続処理や外部アクセスへ渡すことを防ぐため。
def test_untrusted_backlog_url_returns_tool_error() -> None:
    async def scenario() -> None:
        async with Client(build_server(FakeGetIssueContext())) as client:  # type: ignore[arg-type]
            result = await client.call_tool(
                "get_issue_context",
                {"backlog_url": "https://attacker.example/view/TEST-1"},
            )

        assert result.is_error is True
        assert result.structured_content is None

    asyncio.run(scenario())
