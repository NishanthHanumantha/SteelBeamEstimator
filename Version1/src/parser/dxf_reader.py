"""DXF file loading and validation."""

from pathlib import Path
from typing import Optional

from ezdxf.document import Drawing
from ezdxf import recover
from loguru import logger


class DxfReadError(Exception):
    """Raised when a DXF file cannot be read or validated."""


class DxfReader:
    """Loads and validates DXF files using ezdxf."""

    SUPPORTED_ENTITY_TYPES = frozenset(
        {
            "TEXT",
            "MTEXT",
            "INSERT",
            "ATTRIB",
            "LINE",
            "LWPOLYLINE",
            "POLYLINE",
            "DIMENSION",
        }
    )

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path).resolve()

    def read(self) -> Drawing:
        """
        Open the DXF file and return an ezdxf Drawing.

        Uses ezdxf recover mode for files with minor structural issues.

        Raises:
            DxfReadError: If the path is invalid or the file cannot be parsed.
        """
        if not self.file_path.exists():
            raise DxfReadError(f"DXF file not found: {self.file_path}")

        if not self.file_path.is_file():
            raise DxfReadError(f"Path is not a file: {self.file_path}")

        if self.file_path.suffix.lower() != ".dxf":
            logger.warning(
                "File extension is not .dxf: {}", self.file_path.suffix
            )

        logger.info("Reading DXF file: {}", self.file_path)

        try:
            doc, auditor = recover.readfile(str(self.file_path))
        except IOError as exc:
            raise DxfReadError(
                f"Failed to read DXF file: {self.file_path} — {exc}"
            ) from exc
        except Exception as exc:
            raise DxfReadError(
                f"Invalid or corrupted DXF file: {self.file_path} — {exc}"
            ) from exc

        if auditor.has_errors:
            logger.warning(
                "DXF auditor reported {} error(s) in {}",
                len(auditor.errors),
                self.file_path.name,
            )
            for error in auditor.errors:
                logger.debug("DXF auditor error: {}", error)

        logger.info(
            "DXF loaded successfully — version {}, {} layers",
            doc.dxfversion,
            len(list(doc.layers)),
        )
        return doc

    @staticmethod
    def get_modelspace(doc: Drawing) -> Optional[object]:
        """Return the modelspace layout from a Drawing."""
        try:
            return doc.modelspace()
        except Exception as exc:
            logger.error("Failed to access modelspace: {}", exc)
            return None
