from __future__ import annotations

from backlog_mcp.application.get_issue_context import GetIssueContext
from backlog_mcp.backlog.client import BacklogClient
from backlog_mcp.config import Settings
from backlog_mcp.mcp.server import build_server


def main() -> None:
    settings = Settings.from_env()
    use_case = GetIssueContext(settings, lambda: BacklogClient(settings))
    build_server(use_case).run(transport="stdio")


if __name__ == "__main__":
    main()
