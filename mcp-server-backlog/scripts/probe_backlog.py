from __future__ import annotations

import asyncio
import sys

from backlog_mcp.backlog.client import BacklogClient
from backlog_mcp.backlog.url import extract_issue_key
from backlog_mcp.config import ConfigurationError, Settings


async def probe(backlog_url: str) -> None:
    settings = Settings.from_env()
    issue_key = extract_issue_key(backlog_url, settings.base_url)

    async with BacklogClient(settings) as client:
        issue = await client.get_issue(issue_key)
        comments = await client.get_comments(issue_key, settings.max_comments)

    change_log_count = sum(len(comment.change_logs) for comment in comments.items)
    print(f"issue_key={issue.key}")
    print(f"status={issue.status}")
    print(f"comments={len(comments.items)}")
    print(f"comments_truncated={comments.truncated}")
    print(f"change_logs={change_log_count}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/probe_backlog.py <backlog-issue-url>")
    try:
        asyncio.run(probe(sys.argv[1]))
    except (ConfigurationError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
