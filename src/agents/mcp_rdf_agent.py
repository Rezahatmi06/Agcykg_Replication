"""MCP RDF agent wrapper.

Spawns the real MCP agent in a dedicated subprocess so that it runs with
a fresh Python/asyncio state. This avoids the known
``cannot pickle '_asyncio.Future' object`` error that occurs when
``mcp_use.MCPAgent`` is run inside an already-active event loop (such as
LangGraph's), because LangChain's callback/verbose plumbing walks the
agent state which contains gRPC Futures from ``langchain-google-genai``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_RESULT_START = "__MCP_RESULT__"
_RESULT_END = "__END__"


def _extract_payload(stdout_bytes: bytes) -> dict | None:
    """Pull the JSON payload emitted by the runner from its stdout.

    The runner wraps its result between ``__MCP_RESULT__`` / ``__END__`` markers
    so we can safely locate it even if other things were printed to stdout.
    """
    try:
        text = stdout_bytes.decode("utf-8", errors="replace")
    except Exception:
        return None

    start = text.rfind(_RESULT_START)
    if start == -1:
        return None
    start += len(_RESULT_START)
    end = text.find(_RESULT_END, start)
    if end == -1:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


async def run_mcp_agent(question: str) -> str:
    """Execute the MCP RDF agent in an isolated subprocess.

    Returns the agent's final answer as a string, or an error message
    prefixed with ``Error during MCP execution:`` on failure.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    runner_path = project_root / "src" / "agents" / "_mcp_runner.py"

    if not runner_path.exists():
        return f"Error during MCP execution: runner script not found at {runner_path}"

    env = os.environ.copy()
    env["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"
    # LangSmith tracing is a common trigger of the deepcopy -> pickle path
    # that explodes on asyncio.Future; keep it off for the child.
    env["LANGCHAIN_TRACING_V2"] = "false"
    # Make sure child's prints are flushed promptly and go out as UTF-8.
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-X",
            "utf8",
            str(runner_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_root),
            env=env,
        )
    except Exception as e:
        logger.error(f"MCP Agent: failed to spawn subprocess: {e}")
        return f"Error during MCP execution: failed to spawn subprocess: {e}"

    try:
        stdout, stderr = await proc.communicate(
            json.dumps({"question": question}).encode("utf-8")
        )
    except Exception as e:
        logger.error(f"MCP Agent: subprocess communication failed: {e}")
        try:
            proc.kill()
        except Exception:
            pass
        return f"Error during MCP execution: subprocess communication failed: {e}"

    # Forward the child's stderr (verbose logs, tracebacks) so the user still
    # sees what happened inside the agent run.
    if stderr:
        try:
            sys.stderr.write(stderr.decode("utf-8", errors="replace"))
            sys.stderr.flush()
        except Exception:
            pass

    payload = _extract_payload(stdout)
    if payload is None:
        err = (stderr.decode("utf-8", errors="replace").strip()
               if stderr else "no output from MCP subprocess")
        logger.error(f"MCP Agent: could not parse subprocess output. stderr: {err}")
        return f"Error during MCP execution: could not parse subprocess output"

    if payload.get("ok"):
        return str(payload.get("result", ""))

    err_msg = payload.get("error", "unknown error")
    logger.error(f"MCP Agent Error: {err_msg}")
    return f"Error during MCP execution: {err_msg}"
