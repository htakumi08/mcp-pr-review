# GitHub投稿ルール

PRレビュー結果は、GitHub PR Conversationへの通常コメントを標準の投稿先にする。GitHub Review submissionやinline commentは、権限と正確な差分位置を確認できる場合だけ補助的に使う。

## 投稿先の優先順位

| 優先 | 投稿先 | 使用条件 | 備考 |
| --- | --- | --- | --- |
| 1 | PR Conversation通常コメント | GitHubへの投稿を明示され、PRがopenで、Issue comment write権限がある | 標準。レビュー結果全体を1コメントにまとめる |
| 2 | GitHub Review submission `COMMENT` | Pull request review write権限があり、review APIが成功する | 使える場合のみ。`APPROVE` と `REQUEST_CHANGES` は自動選択しない |
| 3 | Inline review comment | 正確なpatch行、side、lineまたはpositionを確定できる | bodyの指摘表から省略せず、重複しない範囲で追加する |
| 4 | チャットのみ | 投稿権限がない、PRがclosed、SHAが変わった、Backlog取得が不完全 | 投稿しない理由と再実行条件を報告する |

## 通常コメント投稿の仕様

- `report-template.md` の6セクションを1つのPR Conversationコメント本文として投稿する。
- body末尾へ重複防止markerを必ず入れる。
- 投稿直前にPR state、base/head SHA、既存コメントを再取得する。
- 同じ投稿者、同じrepo、同じPR番号、同じbase/head SHAのmarkerが既にあれば再投稿しない。
- 投稿後はPRコメント一覧を再取得し、コメントURL、本文内marker、投稿者を確認する。

## Review submissionを使う場合

- actionは `COMMENT` のみ許可する。
- `APPROVE`、`REQUEST_CHANGES`、merge、branch更新は行わない。
- inline commentは、差分上の正確な変更行に紐付けられる指摘だけに限定する。
- review APIが403などで失敗した場合、同じ本文を通常コメントとして投稿できるか試す。
- 通常コメントにも失敗した場合は再試行せず、必要なGitHub権限をユーザーへ報告する。

## 権限不足時の扱い

| 失敗 | 扱い |
| --- | --- |
| repositoryやPRを読めない | 対象repoのGitHub App repository accessを確認してもらう |
| review submissionが403 | Pull requests write権限不足として扱い、通常コメント投稿へfallbackする |
| 通常コメントが403 | Issues write権限不足として扱い、投稿せず設定手順を案内する |
| head SHAが変わった | 古いレビューを投稿せず、新しい差分でレビューし直す |

## 投稿本文の不変条件

- 指摘表、課題コンテキスト、要求トレーサビリティ、15観点、確認範囲、変更概要を含める。
- 指摘IDと要求IDの対応は双方向で一致させる。
- Backlogを確認した場合は、取得したコメント件数、変更履歴件数、partial/truncated有無を記載する。
- API key、secret、private query、不要な個人情報を転載しない。
