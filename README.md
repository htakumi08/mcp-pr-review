# mcp-pr-review

GitHub Pull RequestとBacklog課題を統合し、要求トレーサビリティを作成してから固定15観点でレビューするためのプロジェクトです。

Docker化したPython MCPサーバーと読み取り専用Backlog API clientを実装済みです。`get_issue_context(backlog_url)` は課題本文、全コメント、変更履歴、親・子・関連課題を取得し、レビュー用の1つのstructured responseへ正規化します。

## Runtime

- Base image: `python:3.13.15-slim-bookworm`
- MCP transport: stdio
- Production direct dependencies: `mcp==2.0.0`、`httpx==0.28.1`
- Development direct dependency: `pytest==9.1.1`

公式MCP SDKが必要とする推移依存はインストールされますが、プロジェクトが直接追加するパッケージは上記3つだけです。runtime targetにはpytestをインストールしません。

<<<<<<< Updated upstream
## Development

```bash
docker compose build backlog-mcp
docker compose run --rm --no-deps backlog-mcp pytest
```
=======
PRレビュースキルは、GitHub PR本文・差分・コメント・CI情報と、PR本文または直接参照されたGitHub Issue本文に含まれるBacklog URLの課題情報を統合します。要求を整理した後、固定15観点でレビューし、`【must】（blocking）：中` などのラベル・重大度付き指摘を作成します。

GitHub PR URLを指定してレビューを依頼された場合は、追加の投稿指示を待たず、レビュー後にPR Conversationへ通常コメントを投稿します。「投稿しない」「プレビューのみ」と明示された場合や、PR URLのない一般的なレビューではチャット表示だけにします。GitHub Review submissionやinline commentは、権限と正確な差分位置を確認できる場合だけ補助的に使います。
>>>>>>> Stashed changes

MCPサーバーは次のコマンドでstdio待機状態になります。Codex用の同じ起動設定は`.codex/config.toml`にあります。

```bash
docker compose run --rm --no-deps -T backlog-mcp
```

## Backlog API probe

`.env.example`を参考に、Git管理されない`.env`へ次を設定します。

```dotenv
BACKLOG_BASE_URL=https://your-space.backlog.jp
BACKLOG_API_KEY=your-api-key
```

課題キーの環境変数は不要です。設定後、確認したいBacklog課題URLをコマンド引数に渡します。Docker内から課題本文と設定上限までのコメントを読み取り、本文を表示せず件数だけを確認できます。

```bash
docker compose run --rm --no-deps backlog-mcp \
  python scripts/probe_backlog.py \
  "https://your-space.backlog.jp/view/PROJECT-1"
```

stdio MCPの起動と`tools/call`まで含めて確認する場合は、次を実行します。こちらも本文は表示しません。

```bash
docker compose run --rm --no-deps backlog-mcp \
  python scripts/probe_mcp.py \
  "https://your-space.backlog.jp/view/PROJECT-1"
```

実運用では、PR本文から検出したBacklog URLを `get_issue_context(backlog_url)` へ渡します。MCPがURLのoriginを `BACKLOG_BASE_URL`と照合し、許可されたスペースの`/view/<issue-key>`だけから内部用課題キーを抽出します。

任意設定の既定値は、timeout 10秒、コメント500件、子・関連課題各20件、同一課題cache 60秒です。コメントまたは関連情報の取得に失敗した場合は、取得できた主課題を返しつつ`retrieval.partial`と`retrieval.warnings`で未確認範囲を示します。

## Documents

- [Backlog連携の処理フローとアーキテクチャ](docs/architecture.md)
- [PRレビュースキル](.agents/skills/pr-review/SKILL.md)
- [レビュー観点](.agents/skills/pr-review/references/review-checklist.md)
- [レビュー結果テンプレート](.agents/skills/pr-review/references/report-template.md)
