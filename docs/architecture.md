# Backlog連携PRレビュー・アーキテクチャ

## 1. 目的とスコープ

GitHub Pull Requestの説明と実装差分だけでなく、PRが参照するBacklog課題の本文、コメント、変更履歴を要求の根拠として統合し、固定15観点でレビューする。

初期スコープでは、Backlog MCPは読み取り専用の `get_issue_context` だけを公開する。課題更新、コメント投稿、添付ファイル取得、Wiki・Git操作、GitHubへの書き込みはBacklog MCPの責務に含めない。GitHub PR URL付きのレビュー依頼では、PRレビュースキルがレビュー後にPR Conversationへ通常コメントを投稿する。ユーザーが投稿禁止を明示した場合は投稿しない。

## 2. Redmine構成からの変更点

| 項目 | 旧Redmine構成 | 新Backlog構成 |
| --- | --- | --- |
| 課題管理基盤 | Redmine applicationとDBをDockerで運用 | Backlog SaaSを利用 |
| 自作コンテナ | Redmine MCPに加えてRedmine・DBが必要 | Backlog MCPの1コンテナのみ |
| 課題識別子 | 数値のissue ID | `PROJECT-123`形式のissue key |
| 履歴 | journalsとfield changes | commentsと各commentの`changeLog` |
| 接続制御 | 許可したRedmine host | `BACKLOG_BASE_URL`と完全一致するspaceだけ |
| 主な運用制約 | Redmine・DBの起動、migration、seed | API認証、ページング、レート制限 |

## 3. システム構成

```mermaid
flowchart LR
    U["User"] --> H["MCP host / Codex"]
    H --> S["PR review skill"]
    S --> G["GitHub connector or gh"]
    S -->|"stdio / JSON-RPC"| M["Backlog MCP container"]
    M -->|"HTTPS / Backlog API v2"| B["Backlog SaaS"]
    S --> R["Review report"]
    R -. "PR URL review request" .-> G
```

### 責務境界

| コンポーネント | 責務 | 責務外 |
| --- | --- | --- |
| PRレビュースキル | GitHub情報取得、Backlog URL検出、要求統合、15観点レビュー、出力整形 | Backlog APIの認証・HTTP詳細 |
| Backlog MCP | 課題キー検証、API呼び出し、ページング、正規化、secret除去、構造化エラー | PR解釈、コードレビュー、GitHub投稿 |
| Backlog API client | HTTPS、認証、timeout、response DTO、rate-limit情報の取得 | 要求の意味解釈、MCP schema |
| GitHub連携 | PR、Issue、diff、review、CIの取得とPR URL付きレビュー依頼時の投稿 | Backlogデータの取得 |

## 4. レビュー処理フロー

```mermaid
sequenceDiagram
    actor User
    participant Skill as PR review skill
    participant GitHub
    participant MCP as Backlog MCP
    participant Backlog

    User->>Skill: PRレビューを依頼
    Skill->>GitHub: PR、Issue、comments、diff、CI、SHAを取得
    GitHub-->>Skill: GitHub context
    Skill->>Skill: PR本文からBacklog URLを検出
    opt Backlog課題URLあり
        Skill->>MCP: get_issue_context(backlog_url)
        MCP->>MCP: 許可space検証・issue key抽出
        MCP->>Backlog: GET issue
        Backlog-->>MCP: issue detail
        MCP->>Backlog: GET comments（ページング）
        Backlog-->>MCP: comments + changeLog
        MCP-->>Skill: normalized IssueContext
    end
    Skill->>Skill: 情報源を保持して課題・要求R-xxxを整理
    Skill->>Skill: 要求と実装・test・docsを突合
    Skill->>Skill: 固定15観点で指摘F-xxを作成
<<<<<<< Updated upstream
    Skill-->>User: 6セクションのレビュー結果
    opt GitHub投稿が明示された
        Skill->>GitHub: head SHA再確認後にCOMMENT review投稿
=======
    alt PR URL付きレビュー依頼
        Skill->>GitHub: head SHA再確認後にPR Conversation通常コメントを投稿
        GitHub-->>Skill: 投稿済みコメント
        Skill-->>User: 5セクションのレビュー結果と投稿結果
    else 投稿禁止またはPR URLなし
        Skill-->>User: 5セクションのレビュー結果
>>>>>>> Stashed changes
    end
```

### 詳細手順

1. repository、PR番号、base/head SHAを確定し、PR本文、関連GitHub Issue、discussion、diff、CIを取得する。
2. PR本文と直接参照されたGitHub Issue本文だけからBacklog URLを検出する。
3. Backlog URLごとに `get_issue_context(backlog_url)` を1回呼ぶ。
4. MCPがURLのscheme・host・portを `BACKLOG_BASE_URL` と完全一致させ、`/view/<issue-key>` から内部用課題キーを抽出して課題詳細と全コメントを取得する。
5. MCPはコメントの`changeLog`を分離し、取得件数、切り詰め有無、rate-limit情報を含む正規化結果を返す。
6. スキルはPR、GitHub Issue、Backlog本文、comment、changeLogの出所を保持したまま要求を `R-001` から採番する。
7. 要求と実装、test、設定、docsを突合し、固定15観点をすべて判定する。
8. 指摘を `must`、`question`、`suggestion`、`nitpick` と重大度で分類し、要求IDと双方向に対応付ける。
<<<<<<< Updated upstream
9. プレビューモードではチャットだけに表示する。投稿モードではhead SHAの不変を確認してGitHubへ1件のCOMMENT reviewとして投稿する。
=======
9. PR URL付きレビュー依頼は投稿モードとし、head SHAの不変を確認してGitHub PR Conversationへ1件の通常コメントとして投稿する。投稿禁止が明示された場合とPR URLのない一般レビューはプレビューモードとする。
>>>>>>> Stashed changes

## 5. Backlog MCPツール契約

### Input

```json
{
  "backlog_url": "https://your-space.backlog.jp/view/PROJECT-123"
}
```

利用者とPRレビュースキルは課題キーを組み立てず、PRに記載されたBacklog URLを渡す。MCPが設定済みoriginと`/view/<issue-key>`形式を検証し、Backlog API clientには抽出済み課題キーだけを渡す。

### Output

```json
{
  "issue": {
    "id": 12345,
    "key": "PROJECT-123",
    "project_key": "PROJECT",
    "summary": "...",
    "description": "...",
    "status": "...",
    "priority": "...",
    "assignee": null,
    "parent_issue_id": null,
    "custom_fields": [],
    "created_at": "...",
    "updated_at": "..."
  },
  "comments": [],
  "change_logs": [],
  "relationships": {
    "parent": null,
    "children": [],
    "related": []
  },
  "retrieval": {
    "source_url": "...",
    "retrieved_at": "...",
    "comment_count": 0,
    "comments_truncated": false,
    "children_truncated": false,
    "related_issues_truncated": false,
    "partial": false,
    "warnings": []
  }
}
```

Backlog APIの課題詳細 `GET /api/v2/issues/:issueIdOrKey` とコメント一覧 `GET /api/v2/issues/:issueIdOrKey/comments` を内部で使用する。コメントは古い順に正規化し、API上のページ順を要求の優先順位として扱わない。

### Error

| code | 条件 | retry方針 |
| --- | --- | --- |
| `invalid_backlog_url` | 許可外origin、path、課題キー形式 | retryしない |
| `unauthorized` | API keyが無効 | retryしない |
| `forbidden` | 課題・projectを閲覧できない | retryしない |
| `not_found` | 課題が存在しない | retryしない |
| `rate_limited` | Backlog APIが429を返した | reset情報を返し、MCP内部で長時間待機しない |
| `upstream_timeout` | Backlog APIがtimeout | MCP内ではretryせず、部分取得可能な範囲を返す |
| `upstream_schema_error` | 想定schemaと異なる | retryせず、本文をログへ出さない |
| `partial_result` | コメントなどを最後まで取得できない | 取得済み範囲と未確認範囲を返す |

## 6. 目標ディレクトリ構成

以下は実装完了時の目標構成であり、各コメントはそのファイルまたはディレクトリの責務を表す。`uv.lock`は導入せず、現段階では`pyproject.toml`で3つの直接依存を完全固定する。

```text
mcp-pr-review/
├── .agents/                                      # Codexが利用するPRレビュー手順と参照資料を管理する。
│   └── skills/
│       └── pr-review/                            # GitHubとBacklogを統合するレビューskillを定義する。
│           ├── SKILL.md                          # レビュー全体の必須手順と安全な投稿条件を定義する。
│           ├── agents/
│           │   └── openai.yaml                   # skill一覧に表示する名前・説明・既定promptを定義する。
│           └── references/                       # 必要時だけ読み込む詳細ルールを責務別に分割する。
│               ├── review-checklist.md           # 省略しない固定15観点と判定基準を定義する。
│               ├── severity-and-labels.md        # must等のラベルと重大度を別軸で定義する。
│               ├── report-template.md            # チャットとGitHubで共通のレビュー形式を定義する。
│               ├── github-pr-workflow.md         # GitHub情報取得・SHA固定・重複防止・投稿を定義する。
│               ├── review-context-workflow.md    # 複数情報源から要求とトレーサビリティを作成する。
│               └── backlog-review-workflow.md    # Backlog URL検証・取得・履歴解釈・失敗時動作を定義する。
├── .codex/
│   └── config.toml                               # Docker化したBacklog MCPのstdio起動設定を保持する。
├── src/
│   └── backlog_mcp/                              # Python application packageとしてMCPサーバーを実装する。
│       ├── __init__.py                           # packageの公開versionだけを提供する。
│       ├── __main__.py                           # `python -m backlog_mcp`の薄いentry pointにする。
│       ├── config.py                             # 環境変数を型付き設定へ変換し起動時に検証する。
│       ├── domain/                               # BacklogやMCP frameworkに依存しない内部モデルを置く。
│       │   ├── __init__.py                       # domain packageの公開境界を定義する。
│       │   ├── models.py                         # IssueContext、Comment、ChangeLog等を表現する。
│       │   └── errors.py                         # application全体で使う分類済みerrorを定義する。
│       ├── application/                          # API取得結果をレビュー用contextへ組み立てるuse caseを置く。
│       │   ├── __init__.py                       # application packageの公開境界を定義する。
│       │   └── get_issue_context.py              # 課題・コメント・必要最小限の親子情報を統合する。
│       ├── backlog/                              # Backlog API v2固有の通信と変換を閉じ込める。
│       │   ├── __init__.py                       # Backlog adapterの公開境界を定義する。
│       │   ├── client.py                         # httpxで認証・timeout・pagination・rate limitを扱う。
│       │   ├── url.py                            # 許可spaceの課題URLを検証して内部用課題キーを抽出する。
│       │   ├── dto.py                            # upstream responseを厳格に検証するDTOを定義する。
│       │   ├── mapper.py                         # Backlog DTOをdomain modelへ変換する。
│       │   └── errors.py                         # HTTP statusと通信失敗をdomain errorへ変換する。
│       └── mcp/                                  # MCP protocolへの公開境界だけを担当する。
│           ├── __init__.py                       # MCP adapter packageの公開境界を定義する。
│           ├── server.py                         # MCPServerを生成しtoolを登録する。
│           ├── instructions.py                   # 読み取り専用・許可space等のserver instructionsを定義する。
│           ├── schemas.py                        # tool input/outputの公開schemaを定義する。
│           └── tools/
│               ├── __init__.py                   # tool registrationの公開境界を定義する。
│               └── get_issue_context.py          # MCP引数をuse caseへ渡し構造化結果・errorを返す。
├── tests/                                        # production packageと責務境界を対応させて検証する。
│   ├── unit/                                     # 外部通信なしで各moduleの分岐と変換を高速検証する。
│   │   ├── test_config.py                        # 必須env、URL制約、secret表現を検証する。
│   │   ├── domain/                               # domain modelとerror分類を検証する。
│   │   ├── application/                          # use caseの統合順序・打ち切り・partial結果を検証する。
│   │   ├── backlog/                              # MockTransportでHTTP・pagination・429・redactionを検証する。
│   │   └── mcp/                                  # tool schemaとapplicationへの委譲だけを検証する。
│   ├── integration/
│   │   └── test_stdio.py                         # subprocessのstdioでinitialize・tools/list・tools/callを検証する。
│   ├── contract/
│   │   └── test_backlog_contract.py              # sanitized fixtureがBacklog DTOへ適合することを検証する。
│   └── fixtures/
│       └── backlog/                              # API key・本文の機密情報を除いたresponse fixtureを保持する。
├── evals/                                        # skill全体の判断品質を代表シナリオで評価する。
│   ├── normal-pr.md                              # PRとBacklog要求が一致する正常系を評価する。
│   ├── backlog-spec-gap.md                       # Backlog要求の実装漏れをmustとして検出できるか評価する。
│   ├── ambiguous-backlog-spec.md                 # 矛盾をquestionとして扱い推測しないことを評価する。
│   └── unavailable-backlog.md                    # 取得失敗時に限定レビューへ切り替えることを評価する。
├── docs/
│   └── architecture.md                           # 処理フロー、責務分離、目標構成、テスト方針を説明する。
├── Dockerfile                                    # 非root・stdio前提の最小Python runtime imageを作成する。
├── compose.yaml                                  # local smoke test用にenvとMCP containerを定義する。
├── .dockerignore                                 # secret、VCS、cache、test生成物をbuild contextから除外する。
├── .env.example                                  # secret値を含めず必要な環境変数名だけを示す。
├── .gitignore                                    # API key、virtualenv、cache、coverage生成物を除外する。
├── pyproject.toml                                # Python version、依存、lint、type check、pytest設定を集約する。
└── README.md                                     # 目的、現在の状態、主要文書への入口を提供する。
```

## 7. Pythonパッケージ設計

依存方向は外側から内側への一方向とする。

```text
mcp adapter -> application -> domain
backlog adapter -> domain
bootstrap/config -> mcp adapter + application + backlog adapter
```

- `domain` は `httpx` とMCP SDKをimportしない。
- `application` はBacklog clientのProtocolに依存し、具体的なHTTP clientを直接生成しない。
- `backlog` はMCPの型を返さず、domain modelまたは分類済みerrorを返す。
- `mcp` はHTTP statusやBacklog DTOを解釈せず、application resultを公開schemaへ変換する。
- `__main__.py` だけがconfig、client、use case、serverを組み立てる。

Pythonは公式MCP Python SDK v2を利用し、transportは初期段階ではstdioだけを有効にする。1回の未cache取得では1つの`httpx.AsyncClient`を共有し、課題・コメント・関連情報の取得完了時に必ずcloseする。直接依存はproductionの`mcp==2.0.0`と`httpx==0.28.1`、developmentの`pytest==9.1.1`だけとし、MCP SDKが要求する推移依存を独自依存と混同しない。

## 8. 設定とsecret

| 環境変数 | 必須 | 用途 |
| --- | --- | --- |
| `BACKLOG_BASE_URL` | 必須 | 許可する1つのBacklog space URLを固定する |
| `BACKLOG_API_KEY` | 必須 | Backlog API認証に使用し、表示・ログ・errorから除去する |
| `BACKLOG_TIMEOUT_SECONDS` | 任意 | connect/read/write timeoutを上限付きで設定する |
| `BACKLOG_MAX_COMMENTS` | 任意 | コメント取得の暴走を防ぎ、超過時はpartial結果にする |
| `BACKLOG_MAX_RELATED_ISSUES` | 任意 | 親子・関連課題の展開数を制限する |
| `BACKLOG_CACHE_TTL_SECONDS` | 任意 | 同一process内で同一課題の再取得を抑制するTTL |

API keyはBacklog API仕様上query parameterとして送信するため、request URL、redirect先、例外のrequest表現をログへ出さない。stdoutはMCPのJSON-RPC専用とし、application logはstderrへ出す。

## 9. Docker方針

- Python runtimeとlock済みproduction dependencyだけを含むmulti-stage buildにする。
- non-root user、read-only root filesystem、不要なLinux capabilityなしで動かす。
- API keyをimage、build args、Compose fileへ埋め込まず、実行時envから渡す。
- stdio transportではcontainerのstdinを開き、stdoutへログを混在させない。
- Backlog SaaS以外へのegress制限はDocker単体で完全には保証できないため、application側でもbase URLを固定する。
- Redmine application、DB、volume、migration、seed serviceは構成に含めない。

## 10. テスト方針

| 層 | 主な対象 | 方針 |
| --- | --- | --- |
| Unit | config、validator、mapper、use case、tool adapter | networkとsubprocessを使わず、境界値とerror分岐を網羅する |
| HTTP adapter | Backlog client | `httpx.MockTransport`でpagination、timeout、429、invalid JSON、secret非露出を検証する |
| MCP integration | stdio server | 実subprocessへinitialize、tools/list、tools/callを送りJSON-RPCとstderr分離を検証する |
| Contract | Backlog response DTO | sanitized fixtureで必須・nullable・未知fieldへの互換性を検証する |
| Docker smoke | built image | non-root起動、stdio応答、env不足時のfail-fastを検証する |
| Skill eval | PRレビュー結果 | 要求抽出、15観点、label、traceability、取得失敗時の挙動をシナリオ評価する |

通常CIでは実Backlog spaceへ接続しない。実APIのsmoke testは明示的な手動jobに分離し、読み取り専用アカウント、専用課題、短いtimeout、呼び出し上限を使う。

## 11. 実装順序

1. `python:3.13.15-slim-bookworm`のdevelopment/runtime imageとComposeを作る。完了。
2. `get_issue_context`とstdio integration testを作る。完了。
3. 課題・コメントAPIを接続し、コメントpaginationと変更履歴正規化を作る。完了。
4. 親・子・関連課題、partial結果、TTL cacheを作る。完了。
5. `.codex/config.toml`からDocker Composeのstdioサーバーを起動できるようにする。完了。
6. GitHub PR取得とBacklog MCPを使ったskill evalを整備する。未着手。
3. config、sanitized fixture、DTO、課題・コメント取得client、error変換をtest-firstで作る。完了。
4. 利用者が`.env`を設定し、Docker内のprobeへ課題URLを渡して実Backlog課題とコメントを確認する。利用者確認待ち。
5. `get_issue_context` use caseでAPI clientを統合し、正規化、打ち切り、取得メタデータを実装する。
6. コメントpagination、親子課題、cache、partial resultを追加する。
7. runtime imageをCodex MCP設定へ登録する。
8. PRレビュースキルのevalを実行し、GitHubとBacklogの要求統合を確認する。
