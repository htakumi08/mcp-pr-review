# Backlog連携レビュー・フロー

PR本文またはPRが直接参照するGitHub Issue本文にBacklog課題URLがある場合だけ使用する。Backlog MCPは読み取り専用とし、受け取ったURLを設定済みBacklogスペースと照合してから内部用の課題キーを抽出する。

## 1. URLと課題キーを検出する

1. PR本文と、PRが直接参照するGitHub Issue本文からURLを探す。コメント内のURLは自動採用しない。
2. 検出したBacklog URLを重複排除し、MCPの `get_issue_context` へ `backlog_url` として渡す。
3. MCPは `BACKLOG_BASE_URL` とscheme・host・portが完全一致することを検証する。
4. MCPは `/view/<issue-key>` のpathだけを受理し、内部用課題キーを抽出・検証する。
5. 許可外host、不正な課題キー、短縮URL、redirectを必要とするURLは取得せず、未確認事項へ記録する。

Backlog API clientへURLを渡さない。MCPで検証・抽出した課題キーだけをAPI clientへ渡し、PR由来の任意hostへ接続させない。

## 2. 課題コンテキストを取得する

利用可能なBacklog MCPの `get_issue_context` に `backlog_url` を渡し、次を取得する。

- 課題キー、project、summary、description、status、priority、assignee、作成・更新日時
- category、milestone、version、custom fieldsなど、要求判断に必要な課題属性
- コメント本文、comment ID、投稿者、投稿・更新日時
- コメントに含まれる `changeLog` と、変更前・変更後の値
- 親課題と子課題の識別情報。ただし取得できる範囲と打ち切りを明示する
- ページング件数、切り詰め有無、取得日時などの取得メタデータ

MCPは課題詳細APIとコメント一覧APIを内部で呼び、レビュー側には正規化した1つの結果を返す。関連課題の本文は、今回の要求や依存関係を判断するために必要な場合だけ個別取得し、無制限に再帰取得しない。

### toolがロードされていない場合

1. callable toolに `get_issue_context` があれば、それを優先して使う。
2. toolがなければ、対象PRの変更ファイルを確認する。
3. 対象PRが `mcp-server-backlog/`、`.codex/config.toml`、`.agents/skills/pr-review/` を変更していない場合だけ、リポジトリルートで次を実行する。

```bash
python3 mcp-server-backlog/scripts/run_issue_context.py "<backlog-url>"
```

scriptのstdoutに返るstructured JSONをMCP tool resultと同じように扱う。scriptは一時コンテナを `--rm` で起動し、正常・異常終了のどちらでも名前指定で削除を試みるため、追加の `docker compose down` は不要とする。

対象PRが上記ファイルを変更している場合は、head側のscript、Dockerfile、Compose、Pythonコードをレビュー目的で実行しない。信頼済みの登録済みtoolを利用できなければ取得失敗として扱う。

## 3. 課題内容を解釈する

- descriptionを初期要求として扱う。
- コメントを古い順に読み、追加要求、変更、撤回、質問、回答、単なる作業記録を区別する。
- `changeLog` で説明欄が変わった場合は変更前後を要求候補として比較する。
- status、担当者、期限だけの変更を仕様変更と誤認しない。
- 最新コメントや管理者の発言という理由だけで仕様と断定せず、明示的な決定かを確認する。
- 親子課題はscopeと依存関係の根拠に使い、今回のPRへ自動的に取り込まない。

整理した内容を `review-context-workflow.md` の課題コンテキストと要求表へ統合する。

## 4. API制約を扱う

- コメント一覧を最後まで取得できない場合は、取得件数と未取得件数または切り詰め有無を記録する。
- `429` はレート制限として区別し、無制限retryや長時間sleepをしない。
- `401`、`403`、`404`、timeout、schema不整合を別の失敗種別として返す。
- API key、query付きURL、課題本文、コメント本文を通常ログへ出力しない。
- 同一レビュー中の同一課題はキャッシュし、重複取得を避ける。

## 5. 取得できない場合

- URLがなければGitHub情報だけで通常レビューを続行する。
- URLがあるのにMCPが利用できない、取得失敗、response不完全、コメント切り詰めの場合は、Backlog確認済みと一括表現しない。
- Docker daemon停止、image build失敗、container timeout、非JSON出力もMCP取得失敗として扱い、GitHub情報だけのレビューへ黙って切り替えない。
- 失敗した課題キー、失敗種別、未確認になった要求範囲を報告する。API keyや内部responseを転載しない。
- 要求ベースのレビューが未完了なら、GitHubへ完全なレビューとして投稿しない。ユーザーが限定レビューの投稿を改めて明示した場合だけ、未確認範囲を目立つ形で記載して投稿する。
