from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

EXIT_DOCKER_ERROR = 20
EXIT_MCP_ERROR = 22
EXIT_INVALID_RESULT = 23
DEFAULT_TIMEOUT_SECONDS = 120


class LifecycleError(RuntimeError):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _run_command(
    command: list[str], *, cwd: Path, timeout_seconds: int
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise LifecycleError("docker command is not available", EXIT_DOCKER_ERROR) from exc
    except subprocess.TimeoutExpired as exc:
        raise LifecycleError("Backlog MCP container timed out", EXIT_DOCKER_ERROR) from exc


def _remove_container(project_dir: Path, container_name: str) -> None:
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def fetch_with_docker(
    backlog_url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    project_dir: Path | None = None,
    container_name: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir or Path(__file__).resolve().parents[1]
    container_name = container_name or f"backlog-mcp-review-{uuid.uuid4().hex[:12]}"

    image = _run_command(
        ["docker", "compose", "images", "-q", "backlog-mcp"],
        cwd=project_dir,
        timeout_seconds=timeout_seconds,
    )
    if image.returncode != 0:
        raise LifecycleError("unable to inspect the Backlog MCP image", EXIT_DOCKER_ERROR)

    if not image.stdout.strip():
        build = _run_command(
            ["docker", "compose", "build", "backlog-mcp"],
            cwd=project_dir,
            timeout_seconds=timeout_seconds,
        )
        if build.returncode != 0:
            raise LifecycleError("unable to build the Backlog MCP image", EXIT_DOCKER_ERROR)

    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "--name",
        container_name,
        "--entrypoint",
        "python",
        "backlog-mcp",
        "scripts/run_issue_context.py",
        "--stdio-client",
        backlog_url,
    ]

    try:
        result = _run_command(
            command,
            cwd=project_dir,
            timeout_seconds=timeout_seconds,
        )
    finally:
        _remove_container(project_dir, container_name)

    if result.returncode != 0:
        exit_code = (
            EXIT_MCP_ERROR if result.returncode == EXIT_MCP_ERROR else EXIT_DOCKER_ERROR
        )
        raise LifecycleError("Backlog MCP invocation failed", exit_code)

    try:
        content = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LifecycleError(
            "Backlog MCP returned invalid structured output", EXIT_INVALID_RESULT
        ) from exc

    expected_types = {
        "issue": dict,
        "comments": list,
        "change_logs": list,
        "relationships": dict,
        "retrieval": dict,
    }
    if not isinstance(content, dict) or any(
        not isinstance(content.get(key), expected_type)
        for key, expected_type in expected_types.items()
    ):
        raise LifecycleError(
            "Backlog MCP returned an unexpected result", EXIT_INVALID_RESULT
        )
    return content


async def fetch_from_stdio(backlog_url: str) -> dict[str, Any]:
    from mcp import Client, StdioServerParameters
    from mcp.client.stdio import stdio_client

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backlog_mcp"],
        env=dict(os.environ),
    )
    async with Client(stdio_client(parameters)) as client:
        result = await client.call_tool(
            "get_issue_context", {"backlog_url": backlog_url}
        )

    if result.is_error or result.structured_content is None:
        raise LifecycleError("MCP get_issue_context failed", EXIT_MCP_ERROR)
    return result.structured_content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch structured Backlog issue context through the Docker MCP server."
    )
    parser.add_argument("backlog_url")
    parser.add_argument(
        "--stdio-client",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.stdio_client:
            try:
                content = asyncio.run(fetch_from_stdio(args.backlog_url))
            except LifecycleError:
                raise
            except Exception as exc:
                raise LifecycleError(
                    "MCP get_issue_context failed", EXIT_MCP_ERROR
                ) from exc
        else:
            content = fetch_with_docker(
                args.backlog_url, timeout_seconds=args.timeout_seconds
            )
    except LifecycleError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.exit_code) from None

    print(json.dumps(content, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
