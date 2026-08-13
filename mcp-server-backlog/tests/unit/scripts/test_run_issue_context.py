from __future__ import annotations

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def load_script() -> ModuleType:
    script_path = Path(__file__).parents[3] / "scripts" / "run_issue_context.py"
    spec = importlib.util.spec_from_file_location("run_issue_context", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = load_script()


def completed(command: list[str], *, stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")


class RunIssueContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project_dir = Path("/tmp/backlog-mcp-test")

    # テストケース: 既存imageから一時コンテナを起動し、structured result取得後に明示的な削除を試みる。
    # 必要な理由: MCP tool未ロード時でも課題本文を取得でき、正常終了時にコンテナを残さないことを保証するため。
    def test_fetch_uses_one_shot_container_and_cleans_up(self) -> None:
        calls: list[list[str]] = []
        context = {
            "issue": {"key": "TEST-1"},
            "comments": [],
            "change_logs": [],
            "relationships": {},
            "retrieval": {},
        }

        def fake_run(command: list[str], **kwargs):
            calls.append(command)
            if command[:4] == ["docker", "compose", "images", "-q"]:
                return completed(command, stdout="image-id\n")
            if command[:3] == ["docker", "compose", "run"]:
                return completed(command, stdout=json.dumps(context))
            if command[:3] == ["docker", "rm", "-f"]:
                return completed(command)
            raise AssertionError(command)

        with patch.object(SCRIPT.subprocess, "run", side_effect=fake_run):
            result = SCRIPT.fetch_with_docker(
                "https://example.backlog.jp/view/TEST-1",
                project_dir=self.project_dir,
                container_name="test-backlog-mcp",
            )

        self.assertEqual(result, context)
        run_command = next(
            command for command in calls if command[:3] == ["docker", "compose", "run"]
        )
        self.assertIn("--rm", run_command)
        self.assertIn(["docker", "rm", "-f", "test-backlog-mcp"], calls)

    # テストケース: Compose imageがまだ存在しない場合だけbuildしてから一時コンテナを起動する。
    # 必要な理由: 初回利用者が手動buildを忘れてもfallbackを利用でき、通常利用時の不要な再buildを避けるため。
    def test_fetch_builds_missing_image(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs):
            calls.append(command)
            if command[:4] == ["docker", "compose", "images", "-q"]:
                return completed(command)
            if command[:3] == ["docker", "compose", "build"]:
                return completed(command)
            if command[:3] == ["docker", "compose", "run"]:
                return completed(
                    command,
                    stdout=(
                        '{"issue":{"key":"TEST-1"},"comments":[],'
                        '"change_logs":[],"relationships":{},"retrieval":{}}'
                    ),
                )
            if command[:3] == ["docker", "rm", "-f"]:
                return completed(command)
            raise AssertionError(command)

        with patch.object(SCRIPT.subprocess, "run", side_effect=fake_run):
            SCRIPT.fetch_with_docker(
                "https://example.backlog.jp/view/TEST-1",
                project_dir=self.project_dir,
                container_name="test-backlog-mcp",
            )

        self.assertIn(["docker", "compose", "build", "backlog-mcp"], calls)

    # テストケース: MCPコンテナ実行がtimeoutしても、名前を指定したコンテナの強制削除を試みる。
    # 必要な理由: 通信停止やstdio不具合でレビュー後に孤立コンテナが残ることを防ぐため。
    def test_fetch_cleans_up_after_timeout(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs):
            calls.append(command)
            if command[:4] == ["docker", "compose", "images", "-q"]:
                return completed(command, stdout="image-id\n")
            if command[:3] == ["docker", "compose", "run"]:
                raise subprocess.TimeoutExpired(command, timeout=1)
            if command[:3] == ["docker", "rm", "-f"]:
                return completed(command)
            raise AssertionError(command)

        with patch.object(SCRIPT.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(SCRIPT.LifecycleError, "timed out"):
                SCRIPT.fetch_with_docker(
                    "https://example.backlog.jp/view/TEST-1",
                    project_dir=self.project_dir,
                    container_name="test-backlog-mcp",
                )

        self.assertIn(["docker", "rm", "-f", "test-backlog-mcp"], calls)

    # テストケース: コンテナが成功終了してもstructured JSONでない出力を正常な課題情報として扱わない。
    # 必要な理由: DockerやMCPの予期しないstdoutを要求根拠に混入させ、誤レビューすることを防ぐため。
    def test_fetch_rejects_invalid_structured_output(self) -> None:
        def fake_run(command: list[str], **kwargs):
            if command[:4] == ["docker", "compose", "images", "-q"]:
                return completed(command, stdout="image-id\n")
            if command[:3] == ["docker", "compose", "run"]:
                return completed(command, stdout="not-json")
            if command[:3] == ["docker", "rm", "-f"]:
                return completed(command)
            raise AssertionError(command)

        with patch.object(SCRIPT.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(
                SCRIPT.LifecycleError, "invalid structured output"
            ):
                SCRIPT.fetch_with_docker(
                    "https://example.backlog.jp/view/TEST-1",
                    project_dir=self.project_dir,
                    container_name="test-backlog-mcp",
                )
