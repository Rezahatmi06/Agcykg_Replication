"""Subprocess entry point for running the MCP RDF agent in isolation.

Why a subprocess?
-----------------
The MCP RDF agent uses ``langchain-google-genai`` via ``mcp_use``'s
``MCPAgent``. When invoked from inside the LangGraph workflow's event loop,
LangChain's callback/verbose machinery can end up doing a ``copy.deepcopy``
over state that contains an ``asyncio.Future`` (held by the GenAI gRPC
channel and/or the MCP stdio connector). Python's pickle protocol is used
as a fallback by ``deepcopy``, which then raises::

    TypeError: cannot pickle '_asyncio.Future' object

Running this work in a fresh Python process gives it a clean event loop
and fresh module state. On top of that, we also install a ``deepcopy``
safeguard below that returns the original object when it would otherwise
fail the pickle fallback. This keeps the agent running even if some
callback machinery tries to copy a non-copyable object.

Protocol
--------
* Parent writes a single JSON line to our stdin: ``{"question": "..."}``
* We write exactly one line to stdout, bracketed with markers, containing
  ``{"ok": true, "result": "..."}`` or ``{"ok": false, "error": "..."}``.
* Verbose / log / traceback output goes to stderr so the parent can
  forward it.
"""

from __future__ import annotations

# --- Safety: install deepcopy / pickle guards BEFORE importing anything that
# may hold asyncio.Future objects. -------------------------------------------

import copy as _copy_mod
import pickle as _pickle_mod
import copyreg as _copyreg_mod

_orig_deepcopy = _copy_mod.deepcopy


def _safe_deepcopy(x, memo=None, _nil=[]):  # noqa: B006 (keep signature)
    """deepcopy that falls back to returning ``x`` when pickling fails.

    Some objects (notably ``_asyncio.Future`` and grpc.aio channels) cannot
    be pickled. When ``copy.deepcopy`` walks into them via the pickle
    protocol it raises ``TypeError: cannot pickle ... object``. For the
    agent's purposes, having the same reference is fine — we only copy
    these containers to "snapshot" state for logging/tracing. Returning
    ``x`` is safe because nothing in the agent path actually mutates these
    objects after snapshotting.
    """
    try:
        return _orig_deepcopy(x, memo, _nil)
    except TypeError as e:
        msg = str(e)
        if "cannot pickle" in msg or "cannot be pickled" in msg:
            return x
        raise


_copy_mod.deepcopy = _safe_deepcopy


def _future_reduce(_obj):
    # Make any accidental pickle attempt on a Future resolve to ``None``
    # rather than raising, so downstream code that caches or logs doesn't
    # crash the whole agent run.
    return (type(None), ())


try:
    import asyncio as _asyncio_mod

    _copyreg_mod.dispatch_table[_asyncio_mod.Future] = _future_reduce  # type: ignore[assignment]
except Exception:
    pass

try:
    import _asyncio  # type: ignore[import-not-found]

    _copyreg_mod.dispatch_table[_asyncio.Future] = _future_reduce  # type: ignore[assignment]
except Exception:
    pass


# ---------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Turn off tracing and verbose debug in the child — they are the main
# entry points for the deepcopy/pickle path.
os.environ["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ.pop("LANGCHAIN_ENDPOINT", None)
os.environ.pop("LANGCHAIN_API_KEY", None)


# --- Step-by-step reasoning output --------------------------------------------
# ``mcp_use.MCPAgent.stream`` already calls ``logger.info("💭 Reasoning: ...")``,
# ``logger.info("🔧 Tool call: ...")`` and ``logger.info("📄 Tool result: ...")``
# for each step. These go through Python's logging module, NOT through
# LangChain's StdOutCallbackHandler (which is the component that triggers the
# ``cannot pickle '_asyncio.Future' object`` deepcopy path when ``verbose=True``
# is passed to the AgentExecutor).
#
# So we can safely route the ``mcp_use`` logger to stderr at INFO level to get
# the step-by-step trace back, while keeping ``verbose=False`` on the MCPAgent.
# stderr is chosen so it doesn't collide with the ``__MCP_RESULT__`` marker on
# stdout — the parent (mcp_rdf_agent.py) already forwards child stderr to its
# own stderr, so the user sees it in the terminal in real time.
_MCP_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_mcp_stderr_handler = logging.StreamHandler(sys.stderr)
_mcp_stderr_handler.setFormatter(logging.Formatter(_MCP_LOG_FORMAT))
_mcp_stderr_handler.setLevel(logging.INFO)

_mcp_logger = logging.getLogger("mcp_use")
# Avoid piling up duplicate handlers if this module is ever re-imported.
for _h in list(_mcp_logger.handlers):
    _mcp_logger.removeHandler(_h)
_mcp_logger.addHandler(_mcp_stderr_handler)
_mcp_logger.setLevel(logging.INFO)
_mcp_logger.propagate = False


STRICT_SYSTEM_PROMPT = """
You are a specialized cybersecurity assistant. You MUST answer questions ONLY by using the provided tools. Your only source of information is the knowledge graph accessed via tools.

Your thought process MUST be:
    1.  **Analyze the user's question** to understand the core intent.
    2.  **Select the best tool.**.
    3.  **Execute the tool.** If that fails or the question is complex, use `text_to_sparql` to convert the question into a precise SPARQL query.
    4.  **Analyze the result.**
        - If the result is a **validation error**, correct the arguments and retry.
        - If the result is **empty or "not found"**, try rephrasing your input.
    5.  **NEVER provide an answer from memory.** All answers must be based on tool results.
"""


async def _run(question: str) -> str:
    # Imports inside the function so we can keep early-failure diagnostics
    # clean and to make sure our copy patches above are in place first.
    from langchain.globals import set_debug, set_verbose

    set_debug(False)
    set_verbose(False)

    from mcp_use import MCPAgent, MCPClient

    # Make absolutely sure the mcp_use logger keeps our stderr handler even
    # after the library has loaded (mcp_use.Logger.configure may replace
    # handlers at import/init time). We re-assert INFO + stderr here.
    try:
        from mcp_use.logging import Logger as _McpLogger  # type: ignore
        # Disable console/file handlers managed by the library; we manage
        # output ourselves on stderr. ``log_to_console=False`` prevents the
        # library from pushing a stdout handler that would contaminate the
        # ``__MCP_RESULT__`` marker line.
        _McpLogger.configure(
            level=logging.INFO,
            log_to_console=False,
            log_to_file=False,
        )
    except Exception:
        pass

    _lg = logging.getLogger("mcp_use")
    if _mcp_stderr_handler not in _lg.handlers:
        _lg.addHandler(_mcp_stderr_handler)
    _lg.setLevel(logging.INFO)
    _lg.propagate = False

    from src.config.settings import llm

    # Defensive: null-out the gRPC async client so `_agenerate` falls back
    # to the sync path via ``run_in_executor``. The sync client does not
    # hold asyncio.Future objects, so deepcopy/pickle paths stay clean.
    try:
        llm.async_client = None  # type: ignore[attr-defined]
    except Exception:
        pass

    config_path = PROJECT_ROOT / "browser_mcp.json"
    if not config_path.exists():
        return f"Error: MCP config not found at {config_path}"

    client = MCPClient.from_config_file(str(config_path))
    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=15,
        verbose=False,  # verbose=True triggers StdOutCallbackHandler
        system_prompt=STRICT_SYSTEM_PROMPT,
    )

    try:
        result = await agent.run(question)
    finally:
        try:
            await client.close_all_sessions()
        except Exception:
            pass

    if hasattr(result, "content"):
        return str(result.content)
    if isinstance(result, dict) and "output" in result:
        return str(result["output"])
    return str(result)


def _emit(payload: dict) -> None:
    sys.stdout.write("\n__MCP_RESULT__" + json.dumps(payload) + "__END__\n")
    sys.stdout.flush()


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        _emit({"ok": False, "error": f"Invalid input JSON: {e}"})
        return 1

    question = payload.get("question", "")
    if not question:
        _emit({"ok": False, "error": "Missing 'question' in input payload."})
        return 1

    try:
        result = asyncio.run(_run(question))
        _emit({"ok": True, "result": result})
        return 0
    except Exception as e:
        # Print the full traceback to stderr so the parent can forward it.
        traceback.print_exc(file=sys.stderr)
        _emit({"ok": False, "error": f"{type(e).__name__}: {e}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
