# Sample Laravel application

PRレビュースキルの動作確認に使用するLaravelアプリです。スキルやBacklog MCPサーバーとは独立しており、レビュー対象となるPRを作成するための最小構成を維持します。

## Runtime

- PHP: `8.5-cli-bookworm`
- Dependency manager: Composer 2
- Web server: `php artisan serve`
- Published port: `8000`

## Setup

このディレクトリで実行します。

```bash
docker compose build app
docker compose run --rm app composer install
docker compose run --rm app php artisan key:generate
```

## Run

```bash
docker compose up app
```

起動後は `http://localhost:8000` で確認できます。

## Test

```bash
docker compose run --rm app php artisan test
```

このアプリへ機能を追加する場合も、Laravel標準構成とレビュー検証に必要な範囲を優先し、PRレビュースキルやMCPサーバーの実装を置かないでください。
