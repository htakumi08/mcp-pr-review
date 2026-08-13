# Backlog MCP server

PRレビューに必要なBacklog課題情報を読み取り専用で提供するPython MCPサーバーです。`get_issue_context(backlog_url)` は許可されたBacklogスペースの課題URLだけを受理し、課題本文、コメント、変更履歴、親・子・関連課題を1つのstructured responseへ正規化します。

<br>

## Runtime

- Base image: `python:3.13.15-slim-bookworm`
- MCP transport: stdio
- Production direct dependencies: `mcp==2.0.0`、`httpx==0.28.1`
- Development direct dependency: `pytest==9.1.1`

公式MCP SDKの推移依存はインストールされますが、このサーバーが直接追加するパッケージは上記3つだけです。runtime targetにはpytestをインストールしません。

<br>

## Configuration

`.env.example`を参考に、Git管理されない同ディレクトリの`.env`へ設定します。

```dotenv
BACKLOG_BASE_URL=https://your-space.backlog.jp
BACKLOG_API_KEY=your-api-key
```

課題キーの環境変数は不要です。任意設定の既定値は、timeout 10秒、コメント500件、子・関連課題各20件、同一課題cache 60秒です。

<br>

## Development

このディレクトリでDocker Composeを実行します。

```bash
docker compose build backlog-mcp
docker compose run --rm --no-deps backlog-mcp pytest
```

MCPサーバーをstdio待機状態で起動するコマンドは次のとおりです。

```bash
docker compose run --rm --no-deps -T backlog-mcp
```

リポジトリルートの`.codex/config.toml`も、このCompose構成を使用します。

<br>

## One-shot skill fallback

Codexでproject-scoped MCP toolがロードされていない場合は、リポジトリルートから次のscriptを実行できます。

```bash
python3 mcp-server-backlog/scripts/run_issue_context.py \
  "https://your-space.backlog.jp/view/PROJECT-1"
```

ホスト側の追加Python packageは不要です。scriptはCompose imageがなければ初回だけbuildし、名前付き一時コンテナでstdio MCPの `get_issue_context` を呼び出します。処理後は `--rm` と明示的な `docker rm -f` によってcleanupするため、`docker compose up`、`stop`、`down` は不要です。stdoutにはレビューで使用するstructured JSONだけを出力し、起動・MCP・形式エラーは非0の終了コードで返します。

レビュー対象PRが `mcp-server-backlog/` や起動設定を変更している場合、そのPRのhead側scriptやDocker構成をレビュー目的で実行しないでください。

<br>

## Backlog API probe

確認したいBacklog課題URLを引数に渡します。課題本文やコメント本文は表示せず、取得件数と取得状態だけを確認します。

```bash
docker compose run --rm --no-deps backlog-mcp \
  python scripts/probe_backlog.py \
  "https://your-space.backlog.jp/view/PROJECT-1"
```

stdio MCPの起動から`tools/call`まで確認する場合は、次を実行します。

```bash
docker compose run --rm --no-deps backlog-mcp \
  python scripts/probe_mcp.py \
  "https://your-space.backlog.jp/view/PROJECT-1"
```

MCPはURLのoriginを`BACKLOG_BASE_URL`と照合し、許可されたスペースの`/view/<issue-key>`だけから内部用課題キーを抽出します。コメントや関連情報の取得に失敗した場合は、取得済みの主課題を返し、`retrieval.partial`と`retrieval.warnings`で未確認範囲を示します。

<br>

## Structure

```text
mcp-server-backlog/
├── src/backlog_mcp/     # MCP server、use case、Backlog API adapterを実装する
├── tests/               # unit test、stdio integration test、sanitized fixtureを管理する
├── scripts/             # 実API probe、stdio probe、skill用one-shot lifecycleを提供する
├── Dockerfile           # development/runtimeの最小Python imageを作成する
├── compose.yaml         # ローカル開発とCodex向けstdio起動を定義する
├── pyproject.toml       # Python version、直接依存、pytest設定を管理する
├── .env.example         # 必要な環境変数と既定値を示す
├── .dockerignore        # secret、VCS、cacheをbuild contextから除外する
└── .gitignore           # secret、virtualenv、test生成物を除外する
```
