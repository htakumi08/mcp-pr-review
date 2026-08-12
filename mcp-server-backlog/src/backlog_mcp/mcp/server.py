from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from backlog_mcp.application.get_issue_context import GetIssueContext


def build_server(use_case: GetIssueContext) -> MCPServer:
    server = MCPServer(
        name="backlog-pr-review",
        title="Backlog PR Review",
        description="Read-only Backlog context provider for pull request review",
        instructions=(
            "Use get_issue_context with a Backlog issue URL in the configured space. "
            "The server validates the URL and returns issue, comment, change, and relationship context."
        ),
        version="0.1.0",
        log_level="WARNING",
    )

    @server.tool(
        name="get_issue_context",
        description="Read and normalize review context for a Backlog issue URL.",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    async def get_issue_context(backlog_url: str) -> dict[str, Any]:
        return await use_case.execute(backlog_url)

    return server
