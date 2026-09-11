"""Registry and cache for JSON schema files."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

PHASE = "Phase LLM.2"
MODEL_VERSION = "6.2.0"
SCHEMAS_ROOT = Path(__file__).resolve().parents[3] / "schemas"


@dataclass(frozen=True)
class SchemaEntry:
    schema_name: str
    relative_path: str
    version: str
    description: str

    @property
    def absolute_path(self) -> Path:
        return SCHEMAS_ROOT / self.relative_path


@dataclass
class LoadedSchema:
    cache_key: str
    schema_name: str
    schema_version: str
    schema_path: str
    schema_document: Dict[str, Any]


class SchemaNotFoundError(FileNotFoundError):
    """Raised when a schema is not registered or missing on disk."""


SCHEMA_REGISTRY: Dict[str, SchemaEntry] = {
    "BEAM_REASONING": SchemaEntry(
        "BEAM_REASONING",
        "engineering/beam_reasoning.schema.json",
        "1.0",
        "Beam reasoning structured response schema.",
    ),
    "REINFORCEMENT_PARSER": SchemaEntry(
        "REINFORCEMENT_PARSER",
        "engineering/reinforcement_parser.schema.json",
        "1.0",
        "Reinforcement parser structured response schema.",
    ),
    "ANNOTATION_INTERPRETER": SchemaEntry(
        "ANNOTATION_INTERPRETER",
        "engineering/annotation_interpreter.schema.json",
        "1.0",
        "Annotation interpreter structured response schema.",
    ),
    "QA_VALIDATOR": SchemaEntry(
        "QA_VALIDATOR",
        "engineering/qa_validator.schema.json",
        "1.0",
        "QA validator structured response schema.",
    ),
    "CONFIDENCE": SchemaEntry(
        "CONFIDENCE",
        "shared/confidence.schema.json",
        "1.0",
        "Shared confidence field schema.",
    ),
    "BASE_RESPONSE": SchemaEntry(
        "BASE_RESPONSE",
        "shared/base_response.schema.json",
        "1.0",
        "Shared base response schema.",
    ),
    "SAMPLE_RESPONSE": SchemaEntry(
        "SAMPLE_RESPONSE",
        "examples/sample_response.schema.json",
        "1.0",
        "Sample response schema for integration tests.",
    ),
}


class SchemaRegistry:
    """Load and cache JSON schema documents."""

    def __init__(self) -> None:
        self._cache: Dict[str, LoadedSchema] = {}
        self._validators: Dict[str, Any] = {}

    def get_schema(self, schema_name: str) -> LoadedSchema:
        key = schema_name.upper()
        entry = SCHEMA_REGISTRY.get(key)
        if entry is None:
            raise SchemaNotFoundError(f"Schema not registered: {schema_name}")
        path = entry.absolute_path
        if not path.exists():
            raise SchemaNotFoundError(f"Schema file missing: {path}")

        mtime = path.stat().st_mtime_ns
        cache_key = hashlib.sha256(f"{path}|{mtime}".encode("utf-8")).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        document = json.loads(path.read_text(encoding="utf-8"))
        loaded = LoadedSchema(
            cache_key=cache_key,
            schema_name=key,
            schema_version=entry.version,
            schema_path=str(path),
            schema_document=document,
        )
        self._cache = {cache_key: loaded}
        self._validators.pop(key, None)
        return loaded

    def get_validator(self, schema_name: str) -> Any:
        import jsonschema

        key = schema_name.upper()
        if key in self._validators:
            return self._validators[key]
        loaded = self.get_schema(schema_name)
        validator = jsonschema.Draft202012Validator(loaded.schema_document)
        self._validators[key] = validator
        return validator
