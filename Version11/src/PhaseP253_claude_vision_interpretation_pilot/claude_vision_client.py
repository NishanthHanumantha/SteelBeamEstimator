"""Thin Claude Vision wrapper reusing Version10 llm.ClaudeClient."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Tuple

MODEL_VERSION = "10.7.0"


def _ensure_paths(version10_root: Path) -> Path:
    v10 = Path(version10_root).resolve()
    for p in (str(v10), str(v10 / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return v10


def _ensure_namespace_package(name: str, path: Path) -> None:
    """Register a package namespace without executing its __init__.py."""
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]  # type: ignore[attr-defined]
    mod.__file__ = str(path / "__init__.py")
    sys.modules[name] = mod


def _load_llm_module(mod_name: str, file_path: Path):
    full = f"src.llm.{mod_name}"
    existing = sys.modules.get(full)
    if existing is not None and getattr(existing, "__file__", None):
        return existing
    spec = importlib.util.spec_from_file_location(full, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {full} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


def get_claude_client(version10_root: Path) -> Tuple[Any, Any]:
    """
    Load ClaudeClient + ClaudeConfig without importing src.llm package __init__.

    The package __init__ pulls PromptExecutor / estimator_validation which is
    not required for the P2.5.3 vision pilot and is absent under Version10/src.
    """
    v10 = _ensure_paths(version10_root)
    llm_dir = v10 / "src" / "llm"

    # Ensure src / src.llm namespaces exist without running heavy __init__ chains.
    _ensure_namespace_package("src", v10 / "src")
    # If a failed/partial src.llm import remains, replace with a clean namespace.
    prior = sys.modules.get("src.llm")
    if prior is not None and not getattr(prior, "__path__", None):
        del sys.modules["src.llm"]
    if "src.llm" not in sys.modules or not getattr(sys.modules["src.llm"], "__file__", None):
        # Prefer empty namespace so submodule imports do not execute __init__.py
        if "src.llm" in sys.modules:
            # Already a real package from a previous successful import — keep it.
            pass
        else:
            _ensure_namespace_package("src.llm", llm_dir)

    # If src.llm was fully imported earlier, normal import works.
    # Otherwise load leaf modules by file path.
    try:
        if hasattr(sys.modules.get("src.llm"), "ClaudeClient"):
            from src.llm.claude_client import ClaudeClient  # noqa: WPS433
            from src.llm.claude_config import ClaudeConfig  # noqa: WPS433

            return ClaudeClient(ClaudeConfig), ClaudeConfig
    except Exception:
        pass

    # Clear any half-imported llm submodules that may block reload
    for key in list(sys.modules):
        if key.startswith("src.llm.") and sys.modules[key] is None:
            del sys.modules[key]

    _ensure_namespace_package("src.llm", llm_dir)
    _load_llm_module("claude_config", llm_dir / "claude_config.py")
    _load_llm_module("exceptions", llm_dir / "exceptions.py")
    _load_llm_module("response_parser", llm_dir / "response_parser.py")
    client_mod = _load_llm_module("claude_client", llm_dir / "claude_client.py")
    config_mod = sys.modules["src.llm.claude_config"]
    ClaudeClient = client_mod.ClaudeClient
    ClaudeConfig = config_mod.ClaudeConfig
    return ClaudeClient(ClaudeConfig), ClaudeConfig


def call_claude_vision(
    *,
    version10_root: Path,
    system_prompt: str,
    user_prompt: str,
    images: List[Dict[str, Any]],
    timeout_s: float | None = None,
    max_attempts: int | None = None,
) -> Dict[str, Any]:
    """
    Call Claude with vision evidence.
    Returns audit dict; never includes API key.
    """
    client, config = get_claude_client(version10_root)
    img_payload = [
        {
            "media_type": im.get("media_type") or "image/png",
            "data_base64": im["data_base64"],
            "label": im.get("role"),
        }
        for im in images
        if im.get("data_base64")
    ]
    try:
        result = client.generate_vision_response(
            prompt=user_prompt,
            images=img_payload,
            system_prompt=system_prompt,
            timeout_s=timeout_s,
            max_attempts=max_attempts,
        )
        return {
            "success": True,
            "model": result.get("model") or config.MODEL_NAME,
            "raw_text": result.get("text"),
            "latency_s": result.get("latency_s"),
            "retry_count": result.get("retry_count"),
            "usage": result.get("usage"),
            "estimated_input_tokens": result.get("estimated_input_tokens"),
            "estimated_output_tokens": result.get("estimated_output_tokens"),
            "error": None,
            "error_type": None,
            "temperature": config.TEMPERATURE,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "model": getattr(config, "MODEL_NAME", None),
            "raw_text": None,
            "latency_s": None,
            "retry_count": None,
            "usage": None,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "retry_after_s": getattr(exc, "retry_after_s", None),
            "temperature": getattr(config, "TEMPERATURE", None),
        }


__all__ = ["call_claude_vision", "get_claude_client"]
