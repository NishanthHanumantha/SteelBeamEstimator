"""Load Phase K.2 execution configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "model_version": "6.1.0",
    "phase": "Phase K.2",
    "enable": True,
    "invoke_calculation_engine": True,
    "invoke_steel_bridge": True,
    "invoke_bbs_bridge": True,
    "invoke_excel_bridge": True,
    "invoke_qa_bridge": False,
    "lifecycle_initial": "CREATED",
}


def load_execution_config(config_path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if not config_path.exists():
        return config
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            config.update(payload)
        return config
    except ImportError:
        return _load_simple(config_path, config)


def _load_simple(path: Path, base: dict[str, Any]) -> dict[str, Any]:
    config = dict(base)
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() in {"true", "false"}:
            config[key] = value.lower() == "true"
        else:
            config[key] = value
    return config
