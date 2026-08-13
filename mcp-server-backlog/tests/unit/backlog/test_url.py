from __future__ import annotations

import pytest

from backlog_mcp.backlog.url import BacklogUrlError, extract_issue_key


# テストケース: 設定済みBacklogスペースの標準課題URLから課題キーを抽出する。
# 必要な理由: 利用者にはURLだけを要求し、API client用の課題キーをMCP内部で安全に生成するため。
def test_extracts_issue_key_from_allowed_backlog_url() -> None:
    assert (
        extract_issue_key(
            "https://example.backlog.jp/view/PROJECT-123",
            "https://example.backlog.jp",
        )
        == "PROJECT-123"
    )


# テストケース: 許可originとpathが正しければquery・fragmentを無視して課題キーを抽出する。
# 必要な理由: PRへコピーされた実用的なURLを受理しつつ、query・fragmentをAPIへ転送しないため。
def test_allows_fragment_and_query_without_forwarding_them() -> None:
    assert (
        extract_issue_key(
            "https://example.backlog.jp/view/PROJECT-123?from=pr#comment",
            "https://example.backlog.jp",
        )
        == "PROJECT-123"
    )


# テストケース: 許可外host、HTTP、偽装domain、userinfo、不正pathを課題URLとして拒否する。
# 必要な理由: PR由来URLを使ったSSRF、credential混入、path traversalをMCP境界で防ぐため。
@pytest.mark.parametrize(
    "backlog_url",
    [
        "https://attacker.example/view/PROJECT-123",
        "http://example.backlog.jp/view/PROJECT-123",
        "https://example.backlog.jp.evil.example/view/PROJECT-123",
        "https://user@example.backlog.jp/view/PROJECT-123",
        "https://example.backlog.jp/view/../admin",
        "https://example.backlog.jp/issues/PROJECT-123",
    ],
)
def test_rejects_url_outside_configured_space(backlog_url: str) -> None:
    with pytest.raises(BacklogUrlError):
        extract_issue_key(backlog_url, "https://example.backlog.jp")
