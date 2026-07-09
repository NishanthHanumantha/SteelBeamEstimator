"""Deterministic compression for engineering context."""

from __future__ import annotations

from typing import Any, Dict, List, Set


class ContextCompressor:
    """Remove duplicate values while preserving engineering meaning."""

    def compress_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_values: Set[str] = set()
        seen_headers: Set[str] = set()
        compressed: List[Dict[str, Any]] = []

        for section in sections:
            content = self._compress_value(section.get("content"), seen_values, seen_headers)
            if self._is_empty(content):
                continue
            compressed.append(
                {
                    "section_name": section["section_name"],
                    "priority": section["priority"],
                    "content": content,
                }
            )
        return compressed

    def _compress_value(
        self,
        value: Any,
        seen_values: Set[str],
        seen_headers: Set[str],
        *,
        header: str | None = None,
    ) -> Any:
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for key in sorted(value.keys(), key=lambda item: str(item)):
                child_header = f"{header}.{key}" if header else str(key)
                if child_header in seen_headers:
                    continue
                compressed_child = self._compress_value(
                    value[key],
                    seen_values,
                    seen_headers,
                    header=child_header,
                )
                if self._is_empty(compressed_child):
                    continue
                seen_headers.add(child_header)
                result[str(key)] = compressed_child
            return result

        if isinstance(value, list):
            result_list: List[Any] = []
            for item in value:
                compressed_item = self._compress_value(item, seen_values, seen_headers, header=header)
                if self._is_empty(compressed_item):
                    continue
                signature = repr(compressed_item)
                if signature in seen_values:
                    continue
                seen_values.add(signature)
                result_list.append(compressed_item)
            return result_list

        signature = repr(value)
        if signature in seen_values:
            return None
        seen_values.add(signature)
        return value

    @staticmethod
    def compression_ratio(original_size: int, compressed_size: int) -> float:
        if original_size <= 0:
            return 1.0
        return round(compressed_size / original_size, 4)

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return True
        return False
