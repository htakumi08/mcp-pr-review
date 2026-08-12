from __future__ import annotations

import pytest

from backlog_mcp.config import ConfigurationError, Settings


# テストケース: 必須環境変数から設定を生成し、URL正規化と既定timeoutを確認する。
# 必要な理由: Docker起動時の設定が意図した内部表現へ変換されないとAPI接続全体が失敗するため。
def test_settings_loads_required_environment() -> None:
    settings = Settings.from_mapping(
        {
            "BACKLOG_BASE_URL": "https://example.backlog.jp/",
            "BACKLOG_API_KEY": "secret-value",
        }
    )

    assert settings.base_url == "https://example.backlog.jp"
    assert settings.api_key == "secret-value"
    assert settings.timeout_seconds == 10.0
    assert settings.max_comments == 500
    assert settings.max_related_issues == 20
    assert settings.cache_ttl_seconds == 60.0


# テストケース: HTTP、path・query付きURL、不正文字列をBACKLOG_BASE_URLとして拒否する。
# 必要な理由: APIキーの平文送信や、設定ミスによる意図しないendpointへの接続を防ぐため。
@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.backlog.jp",
        "https://example.backlog.jp/path",
        "https://example.backlog.jp?apiKey=secret",
        "not-a-url",
    ],
)
def test_settings_rejects_unsafe_base_url(base_url: str) -> None:
    with pytest.raises(ConfigurationError, match="BACKLOG_BASE_URL"):
        Settings.from_mapping(
            {
                "BACKLOG_BASE_URL": base_url,
                "BACKLOG_API_KEY": "secret-value",
            }
        )


# テストケース: SettingsのreprにAPIキーの実値が含まれないことを確認する。
# 必要な理由: 例外、デバッグ出力、ログを経由したcredential漏えいを防ぐため。
def test_settings_does_not_expose_api_key_in_repr() -> None:
    settings = Settings.from_mapping(
        {
            "BACKLOG_BASE_URL": "https://example.backlog.jp",
            "BACKLOG_API_KEY": "do-not-print-this",
        }
    )

    assert "do-not-print-this" not in repr(settings)


# テストケース: 件数上限とcache TTLの不正値を起動設定として拒否する。
# 必要な理由: 設定ミスによる無制限取得、過大context、長時間のstale cacheを防ぐため。
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BACKLOG_MAX_COMMENTS", "0"),
        ("BACKLOG_MAX_RELATED_ISSUES", "101"),
        ("BACKLOG_CACHE_TTL_SECONDS", "3601"),
    ],
)
def test_settings_rejects_out_of_range_retrieval_limits(
    name: str, value: str
) -> None:
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_mapping(
            {
                "BACKLOG_BASE_URL": "https://example.backlog.jp",
                "BACKLOG_API_KEY": "secret-value",
                name: value,
            }
        )
