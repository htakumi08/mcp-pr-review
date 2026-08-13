# mcp-pr-review

GitHub Pull RequestとBacklog課題を統合し、要求トレーサビリティを作成してから固定15観点でレビューするためのプロジェクトです。

<br>

## Components

| Component | Location | Responsibility |
| --- | --- | --- |
| PR review skill | [`.agents/skills/pr-review/`](.agents/skills/pr-review/) | GitHub PRとBacklog課題から要求を整理し、固定15観点でレビューして結果を整形・投稿する |
| Backlog MCP server | [`mcp-server-backlog/`](mcp-server-backlog/) | Backlog課題URLを検証し、課題・コメント・変更履歴・関連情報を読み取り専用で取得する |
| Sample application | [`sample-app/`](sample-app/) | PRレビュースキルの動作確認に使用するLaravelアプリを提供する |

3つのコンポーネントは責務と開発環境を分離して管理します。PRレビュースキルはBacklog APIの通信詳細を持たず、Backlog MCPサーバーはPR解釈やGitHub投稿を行いません。`sample-app`はレビュー対象の検証用アプリであり、スキルやMCPサーバーの実装には依存しません。

<br>

## Review workflow

PRレビュースキルは、GitHub PR本文・差分・コメント・CI情報と、PR本文または直接参照されたGitHub Issue本文に含まれるBacklog URLの課題情報を統合します。要求を整理した後、固定15観点でレビューし、`【must】（blocking）：中` などのラベル・重大度付き指摘を作成します。

GitHub PR URLを指定してレビューを依頼された場合は、追加の投稿指示を待たず、レビュー後にPR Conversationへ通常コメントを投稿します。「投稿しない」「プレビューのみ」と明示された場合や、PR URLのない一般的なレビューではチャット表示だけにします。GitHub Review submissionやinline commentは、権限と正確な差分位置を確認できる場合だけ補助的に使います。

<br>

## Setup

Backlog MCPサーバーの環境構築、テスト、実API probeは [`mcp-server-backlog/README.md`](mcp-server-backlog/README.md) を参照してください。プロジェクトスコープのCodex設定は [`.codex/config.toml`](.codex/config.toml) にあり、同ディレクトリのDocker Composeをstdio MCPとして起動します。toolがロードされていない場合はone-shot fallback scriptが一時コンテナを起動・削除し、同じ `get_issue_context` を呼び出します。

`sample-app`は独立したCompose構成を持ちます。起動方法は [`sample-app/README.md`](sample-app/README.md) を参照してください。

<br>

## Documents

- [Backlog連携の処理フローと全体アーキテクチャ](docs/architecture.md)
- [PRレビュースキル](.agents/skills/pr-review/SKILL.md)
- [レビュー観点](.agents/skills/pr-review/references/review-checklist.md)
- [レビュー結果テンプレート](.agents/skills/pr-review/references/report-template.md)
- [GitHub投稿ルール](.agents/skills/pr-review/references/posting-rules.md)
