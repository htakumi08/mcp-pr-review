from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from backlog_mcp.backlog.client import BacklogClient
from backlog_mcp.backlog.errors import (
    BacklogForbiddenError,
    BacklogNotFoundError,
    BacklogRateLimitedError,
    BacklogSchemaError,
    BacklogTimeoutError,
    BacklogUnauthorizedError,
)
from backlog_mcp.config import Settings

FIXTURES = Path(__file__).parents[2] / "fixtures" / "backlog"
API_KEY = "api-key-must-not-leak"


def load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_client(handler: httpx.MockTransport) -> BacklogClient:
    settings = Settings(
        base_url="https://example.backlog.jp",
        api_key=API_KEY,
        timeout_seconds=1.0,
    )
    http_client = httpx.AsyncClient(transport=handler)
    return BacklogClient(settings=settings, http_client=http_client)


# テストケース: 課題取得APIのpath・認証parameterと、レビューに必要な最小fieldの変換を確認する。
# 必要な理由: Backlogの生JSONと内部modelの対応ずれが要求抽出の欠落につながるため。
def test_get_issue_maps_minimum_review_fields() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v2/issues/TEST-1"
            assert request.url.params["apiKey"] == API_KEY
            return httpx.Response(200, json=load_fixture("issue.json"))

        client = make_client(httpx.MockTransport(handler))
        try:
            issue = await client.get_issue("TEST-1")
        finally:
            await client.aclose()

        assert issue.key == "TEST-1"
        assert issue.summary == "Sanitized MCP review issue"
        assert issue.status == "Open"
        assert issue.assignee is None

    asyncio.run(scenario())


# テストケース: 親課題IDを正の数値identifierとして課題取得endpointへ渡せることを確認する。
# 必要な理由: 主課題のparentIssueIdから親課題情報を補完する経路が課題キー専用検証で壊れないため。
def test_get_issue_accepts_numeric_parent_identifier() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v2/issues/12345"
            return httpx.Response(200, json=load_fixture("issue.json"))

        client = make_client(httpx.MockTransport(handler))
        try:
            issue = await client.get_issue(12345)
        finally:
            await client.aclose()

        assert issue.id == 12345

    asyncio.run(scenario())


# テストケース: コメントを昇順で取得し、changeLogを内部modelへ変換する。
# 必要な理由: コメントと変更履歴の時系列を誤ると、最新要求や撤回済み要求を誤判定するため。
def test_get_comments_maps_change_logs() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v2/issues/TEST-1/comments"
            assert request.url.params["count"] == "100"
            assert request.url.params["order"] == "asc"
            return httpx.Response(200, json=load_fixture("comments.json"))

        client = make_client(httpx.MockTransport(handler))
        try:
            comments = await client.get_comments("TEST-1", 500)
        finally:
            await client.aclose()

        assert [comment.id for comment in comments.items] == [2001, 2002]
        assert comments.items[1].change_logs[0].field == "status"
        assert comments.items[1].change_logs[0].original_value == "Open"
        assert comments.truncated is False

    asyncio.run(scenario())


# テストケース: コメントが1回の上限を超える場合にminIdで続きを取得し、指定上限超過を通知する。
# 必要な理由: 長い議論の後半にある要求変更の欠落と、取得済みという誤表示を防ぐため。
def test_get_comments_paginates_and_reports_truncation() -> None:
    async def scenario() -> None:
        fixture = load_fixture("comments.json")
        assert isinstance(fixture, list)
        first_page = [{**fixture[0], "id": 2001 + index} for index in range(100)]
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                assert request.url.params["count"] == "100"
                return httpx.Response(200, json=first_page)
            assert request.url.params["count"] == "1"
            assert request.url.params["minId"] == "2101"
            extra = {**fixture[0], "id": 2101}
            return httpx.Response(200, json=[extra])

        client = make_client(httpx.MockTransport(handler))
        try:
            page = await client.get_comments("TEST-1", 100)
        finally:
            await client.aclose()

        assert len(page.items) == 100
        assert page.items[-1].id == 2100
        assert page.truncated is True

    asyncio.run(scenario())


# テストケース: 子課題と関連課題を各専用endpointから取得し、上限超過を切り詰める。
# 必要な理由: scope・依存関係を取得しつつ、関連課題数に比例した無制限なcontext増加を防ぐため。
def test_get_relationships_uses_read_only_endpoints_and_limits_results() -> None:
    async def scenario() -> None:
        fixture = load_fixture("issue.json")
        assert isinstance(fixture, dict)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/v2/issues":
                assert request.url.params["parentIssueId[]"] == "12345"
            else:
                assert request.url.path == "/api/v2/issues/TEST-1/relatedIssues"
            return httpx.Response(
                200,
                json=[fixture, {**fixture, "id": 12346, "issueKey": "TEST-2"}],
            )

        client = make_client(httpx.MockTransport(handler))
        try:
            children = await client.get_child_issues(12345, 1)
            related = await client.get_related_issues("TEST-1", 1)
        finally:
            await client.aclose()

        assert children.items[0].key == "TEST-1"
        assert children.truncated is True
        assert related.items[0].key == "TEST-1"
        assert related.truncated is True

    asyncio.run(scenario())


# テストケース: 401・403・404を個別のdomain errorへ分類し、APIキーを例外から除外する。
# 必要な理由: 認証失敗・権限不足・課題不存在を区別しつつ、失敗経路でsecretを漏らさないため。
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, BacklogUnauthorizedError),
        (403, BacklogForbiddenError),
        (404, BacklogNotFoundError),
    ],
)
def test_http_error_is_classified_without_leaking_api_key(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json={"errors": [{"message": "failed"}]})

        client = make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(expected_error) as exc_info:
                await client.get_issue("TEST-1")
        finally:
            await client.aclose()

        assert API_KEY not in str(exc_info.value)
        assert API_KEY not in repr(exc_info.value)

    asyncio.run(scenario())


# テストケース: 429のreset時刻を保持したrate-limit errorを返し、APIキーを露出しないことを確認する。
# 必要な理由: 呼び出し側が再試行可能時刻を判断し、無制限retryとsecret漏えいを防ぐため。
def test_rate_limit_includes_reset_without_leaking_api_key() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                headers={"X-RateLimit-Reset": "1786543200"},
                json={"errors": [{"message": "rate limited"}]},
            )

        client = make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(BacklogRateLimitedError) as exc_info:
                await client.get_issue("TEST-1")
        finally:
            await client.aclose()

        assert exc_info.value.reset_at == "1786543200"
        assert API_KEY not in str(exc_info.value)

    asyncio.run(scenario())


# テストケース: HTTP 200でも課題objectではないresponseをschema errorとして拒否する。
# 必要な理由: upstream仕様変更や異常responseを正常な課題としてレビューへ渡さないため。
def test_invalid_response_shape_is_rejected() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=["unexpected"])

        client = make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(BacklogSchemaError):
                await client.get_issue("TEST-1")
        finally:
            await client.aclose()

    asyncio.run(scenario())


# テストケース: httpxのtimeout詳細を固定したdomain errorへ変換し、request情報を隠す。
# 必要な理由: request URLにquery parameterとして含まれるAPIキーが例外経由で漏れるのを防ぐため。
def test_timeout_is_sanitized() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("secret transport detail", request=request)

        client = make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(BacklogTimeoutError) as exc_info:
                await client.get_issue("TEST-1")
        finally:
            await client.aclose()

        assert str(exc_info.value) == "Backlog API request timed out"
        assert API_KEY not in repr(exc_info.value)

    asyncio.run(scenario())


# テストケース: path traversal形式の不正な課題キーをHTTP request送信前に拒否する。
# 必要な理由: 外部入力からBacklog APIの想定外pathへアクセスする経路を作らないため。
def test_issue_key_is_validated_before_request() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("request must not be sent")

        client = make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(ValueError, match="issue key"):
                await client.get_issue("../admin")
        finally:
            await client.aclose()

    asyncio.run(scenario())
