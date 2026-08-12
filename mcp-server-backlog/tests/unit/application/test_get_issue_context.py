from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backlog_mcp.application.get_issue_context import GetIssueContext
from backlog_mcp.backlog.client import Page
from backlog_mcp.backlog.dto import parse_comments, parse_issue
from backlog_mcp.backlog.errors import BacklogTimeoutError
from backlog_mcp.config import Settings

FIXTURES = Path(__file__).parents[2] / "fixtures" / "backlog"


def load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeClient:
    def __init__(
        self, *, fail_related: bool = False, truncate_comments: bool = False
    ) -> None:
        self.calls = 0
        self.fail_related = fail_related
        self.truncate_comments = truncate_comments

    async def __aenter__(self) -> FakeClient:
        self.calls += 1
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get_issue(self, issue_id_or_key: str | int):
        return parse_issue(load_fixture("issue.json"))

    async def get_comments(self, issue_key: str, max_items: int):
        return Page(
            tuple(parse_comments(load_fixture("comments.json"))),
            self.truncate_comments,
        )

    async def get_child_issues(self, parent_issue_id: int, max_items: int):
        return Page((), False)

    async def get_related_issues(self, issue_key: str, max_items: int):
        if self.fail_related:
            raise BacklogTimeoutError("timeout")
        return Page((), False)


def make_settings() -> Settings:
    return Settings(
        base_url="https://example.backlog.jp",
        api_key="secret",
        cache_ttl_seconds=60,
    )


# テストケース: 課題・コメント・変更履歴・関連情報を正規化した1つのreview contextへ統合する。
# 必要な理由: PRレビューがBacklog上の初期要求と後続議論を同じ取得結果から追跡できるようにするため。
def test_execute_composes_complete_review_context() -> None:
    async def scenario() -> None:
        client = FakeClient()
        use_case = GetIssueContext(make_settings(), lambda: client)
        result = await use_case.execute("https://example.backlog.jp/view/TEST-1")

        assert result["issue"]["description"].startswith("Initial requirement")
        assert len(result["comments"]) == 2
        assert result["change_logs"][0]["field"] == "status"
        assert result["retrieval"]["partial"] is False

    asyncio.run(scenario())


# テストケース: 任意の関連情報だけ取得失敗した場合、主課題を返しつつ失敗元をpartial警告へ記録する。
# 必要な理由: 一部API障害時に全コンテキストを失わず、未確認範囲をレビュー側が明示できるようにするため。
def test_execute_returns_sanitized_partial_result_for_optional_failure() -> None:
    async def scenario() -> None:
        client = FakeClient(fail_related=True)
        use_case = GetIssueContext(make_settings(), lambda: client)
        result = await use_case.execute("https://example.backlog.jp/view/TEST-1")

        assert result["issue"]["key"] == "TEST-1"
        assert result["retrieval"]["partial"] is True
        assert result["retrieval"]["warnings"] == [
            {"source": "related_issues", "error": "BacklogTimeoutError"}
        ]

    asyncio.run(scenario())


# テストケース: 同じ課題URLをTTL内に再取得した場合、Backlog clientを再度起動せずcacheを返す。
# 必要な理由: 同一レビュー中の重複API呼び出しとレート制限消費を抑えるため。
def test_execute_caches_same_issue_within_ttl() -> None:
    async def scenario() -> None:
        client = FakeClient()
        use_case = GetIssueContext(make_settings(), lambda: client)
        url = "https://example.backlog.jp/view/TEST-1"

        first = await use_case.execute(url)
        second = await use_case.execute(url)

        assert second is first
        assert client.calls == 1

    asyncio.run(scenario())


# テストケース: コメント取得上限を超えた結果をpartialとして明示する。
# 必要な理由: コメントが返っていても全履歴確認済みと誤認し、後半の要求変更を見落とすのを防ぐため。
def test_execute_marks_truncated_comments_as_partial() -> None:
    async def scenario() -> None:
        client = FakeClient(truncate_comments=True)
        use_case = GetIssueContext(make_settings(), lambda: client)
        result = await use_case.execute("https://example.backlog.jp/view/TEST-1")

        assert result["retrieval"]["comments_truncated"] is True
        assert result["retrieval"]["partial"] is True

    asyncio.run(scenario())
