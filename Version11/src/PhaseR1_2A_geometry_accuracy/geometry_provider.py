"""
geometry_provider.py — Official single production geometry interface.
MODEL_VERSION: 8.3.0

Every downstream module obtains beam geometry ONLY through this provider.
Multi-source evidence selection — never first-found / cached / global max.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.3.0"


@dataclass
class BeamGeometry:
    beam_id: str
    clear_span_mm: Optional[float]
    width_mm: Optional[float]
    depth_mm: Optional[float]
    source: str = "UNKNOWN"
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    drawing_source: str = ""
    effective_span_mm: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["effective_span_mm"] is None:
            d["effective_span_mm"] = d["clear_span_mm"]
        return d


def _dist_point_seg(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class GeometryProvider:
    """
    Single production geometry interface.

    Resolution order (evidence-scored, not first-found):
      1. Framing plan LINE/LWPOLYLINE length near beam label
      2. Reinforcement DXF DIMENSION near beam label
      3. Beam registry (only if span is unique / not a constant-span anomaly)
    """

    REGISTRY_REL = "PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"
    MANIFEST_REL = "PhaseVROOT.1_dynamic_pipeline_initialization/drawing_manifest.json"
    CATALOG_REL = "PhaseR1_2A_geometry_accuracy/validated_beam_geometry.json"

    def __init__(
        self,
        v7_root: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
        run_root: Optional[pathlib.Path] = None,
    ):
        # Prefer explicit output_root; else run_root/data/output; else legacy v7_root/data/output
        if output_root is not None:
            self._out = pathlib.Path(output_root)
        elif run_root is not None:
            self._out = pathlib.Path(run_root) / "data" / "output"
        elif v7_root is not None:
            self._out = pathlib.Path(v7_root) / "data" / "output"
        else:
            raise ValueError("output_root, run_root, or v7_root required")
        self._v7 = self._out  # backward-compat alias for path joins below
        self._geometries: Dict[str, BeamGeometry] = {}
        self._source_audit: Dict[str, Any] = {}
        self._loaded = False

    def load(self, force_resolve: bool = True) -> "GeometryProvider":
        registry = self._read_json(self._out / self.REGISTRY_REL)
        beams = registry.get("beams", {})
        if isinstance(beams, list):
            beams = {b.get("beam_id"): b for b in beams}

        framing_spans = self._extract_framing_spans()
        reinf_spans = self._extract_reinforcement_spans(beams)
        registry_spans = self._registry_spans(beams)

        constant_span = self._detect_constant_span(registry_spans)
        reg_freq = Counter(round(v, 0) for v in registry_spans.values())
        # Any registry value shared by >=3 beams is treated as a leftover
        # constant-span placeholder, even if it is no longer a majority.
        shared_registry_spans = {val for val, cnt in reg_freq.items() if cnt >= 3}

        for beam_id, rec in sorted(beams.items()):
            section = rec.get("section") or {}
            width = float(section.get("width_mm") or 0) or None
            depth = float(section.get("depth_mm") or 0) or None

            candidates: List[Tuple[float, float, str, List[str]]] = []
            # (span, confidence, source, evidence)

            if beam_id in framing_spans:
                span, conf, evid = framing_spans[beam_id]
                candidates.append((span, conf, "FRAMING_PLAN_LINE", evid))

            if beam_id in reinf_spans:
                span, conf, evid = reinf_spans[beam_id]
                candidates.append((span, conf, "REINFORCEMENT_DIMENSION", evid))

            reg_span = registry_spans.get(beam_id)
            if reg_span:
                rounded = round(reg_span, 0)
                is_constant = (
                    (constant_span is not None and rounded == constant_span)
                    or rounded in shared_registry_spans
                )
                if not is_constant:
                    candidates.append((
                        reg_span, 0.55, "BEAM_REGISTRY",
                        [f"registry clear_span_mm={reg_span}"],
                    ))

            if not candidates:
                self._geometries[beam_id] = BeamGeometry(
                    beam_id=beam_id,
                    clear_span_mm=None,
                    width_mm=width,
                    depth_mm=depth,
                    source="MISSING",
                    confidence=0.0,
                    evidence=["No validated span source"],
                    drawing_source="",
                )
                continue

            candidates.sort(key=lambda c: c[1], reverse=True)
            span, conf, source, evid = candidates[0]
            self._geometries[beam_id] = BeamGeometry(
                beam_id=beam_id,
                clear_span_mm=round(float(span), 3),
                width_mm=width,
                depth_mm=depth,
                source=source,
                confidence=round(conf, 3),
                evidence=evid,
                drawing_source=source,
                effective_span_mm=round(float(span), 3),
            )

        self._source_audit = {
            "beam_count": len(self._geometries),
            "framing_hits": len(framing_spans),
            "reinforcement_hits": len(reinf_spans),
            "registry_constant_span_rejected": constant_span or (
                sorted(shared_registry_spans)[0] if shared_registry_spans else None
            ),
            "shared_registry_spans_rejected": sorted(shared_registry_spans),
            "source_counts": dict(Counter(g.source for g in self._geometries.values())),
            "unique_spans": len({
                round(g.clear_span_mm, 0)
                for g in self._geometries.values()
                if g.clear_span_mm
            }),
            "missing_spans": sum(1 for g in self._geometries.values() if not g.clear_span_mm),
        }
        self._loaded = True
        if force_resolve:
            self.export_catalog()
            self.patch_registry()
        return self

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, beam_id: str) -> Optional[BeamGeometry]:
        if not self._loaded:
            self.load()
        return self._geometries.get(beam_id)

    def get_span_mm(self, beam_id: str) -> Optional[float]:
        g = self.get(beam_id)
        return g.clear_span_mm if g else None

    def get_all(self) -> Dict[str, BeamGeometry]:
        if not self._loaded:
            self.load()
        return dict(self._geometries)

    def summary(self) -> Dict[str, Any]:
        if not self._loaded:
            self.load()
        return {
            "provider": "GeometryProvider",
            "model_version": MODEL_VERSION,
            "audit": self._source_audit,
            "is_only_production_source": True,
        }

    def export_catalog(self) -> pathlib.Path:
        out = self._out / self.CATALOG_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_version": MODEL_VERSION,
            "source": "GeometryProvider",
            "beam_count": len(self._geometries),
            "audit": self._source_audit,
            "geometries": {bid: g.to_dict() for bid, g in sorted(self._geometries.items())},
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def patch_registry(self) -> int:
        """Write validated spans back into beam_registry.json.

        Always clears previously rejected constant-span placeholders so
        downstream modules cannot fall back to 8775 mm.
        """
        path = self._out / self.REGISTRY_REL
        if not path.exists():
            return 0
        data = self._read_json(path)
        beams = data.get("beams", {})
        patched = 0
        rejected = self._source_audit.get("registry_constant_span_rejected")
        shared_rejected = set(self._source_audit.get("shared_registry_spans_rejected") or [])
        if rejected is not None:
            shared_rejected.add(float(rejected))
        if isinstance(beams, dict):
            for bid, rec in beams.items():
                g = self._geometries.get(bid)
                if g and g.clear_span_mm:
                    rec["clear_span_mm"] = g.clear_span_mm
                    rec["span_source"] = g.source
                    rec["span_confidence"] = g.confidence
                    patched += 1
                else:
                    # Remove placeholder / unresolved constant spans
                    old = rec.get("clear_span_mm")
                    if old is not None and round(float(old), 0) in shared_rejected:
                        rec["clear_span_mm"] = None
                        rec["span_source"] = "CLEARED_CONSTANT_PLACEHOLDER"
                        patched += 1
                    elif g and g.source == "MISSING":
                        rec["clear_span_mm"] = None
                        rec["span_source"] = "MISSING"
                        patched += 1
            data["beams"] = beams
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return patched

    # ── Source extractors ─────────────────────────────────────────────────

    def _registry_spans(self, beams: Dict[str, Any]) -> Dict[str, float]:
        out = {}
        for bid, rec in beams.items():
            s = rec.get("clear_span_mm")
            if s is not None and float(s) > 0:
                out[bid] = float(s)
        return out

    @staticmethod
    def _detect_constant_span(spans: Dict[str, float]) -> Optional[float]:
        if len(spans) < 3:
            return None
        rounded = [round(v, 0) for v in spans.values()]
        most, count = Counter(rounded).most_common(1)[0]
        if count / len(spans) >= 0.5:
            return most
        return None

    def _extract_framing_spans(self) -> Dict[str, Tuple[float, float, List[str]]]:
        manifest = self._read_json(self._out / self.MANIFEST_REL)
        framing = manifest.get("primary_framing_drawing")
        if not framing or not pathlib.Path(framing).exists():
            return {}
        try:
            import ezdxf
        except ImportError:
            return {}

        doc = ezdxf.readfile(str(framing))
        msp = doc.modelspace()
        labs = self._extract_labels(msp)
        segs = self._extract_segments(msp)
        result: Dict[str, Tuple[float, float, List[str]]] = {}

        for bid, pts in labs.items():
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            cands = []
            for length, x1, y1, x2, y2 in segs:
                d = _dist_point_seg(cx, cy, x1, y1, x2, y2)
                if d <= 600.0:
                    cands.append((d, length))
            if not cands:
                continue
            cands.sort()
            d0 = cands[0][0]
            # Tight local band around closest segment
            local = [c for c in cands if c[0] <= d0 + 40]
            best_len = max(local, key=lambda t: t[1])[1]
            conf = max(0.35, 0.95 - d0 / 900.0)
            result[bid] = (
                best_len, conf,
                [f"framing line length={best_len:.1f} dist={d0:.1f}"],
            )
        return result

    def _extract_reinforcement_spans(
        self, beams: Dict[str, Any]
    ) -> Dict[str, Tuple[float, float, List[str]]]:
        manifest = self._read_json(self._out / self.MANIFEST_REL)
        reinf = manifest.get("primary_reinforcement_drawing")
        if not reinf or not pathlib.Path(reinf).exists():
            return {}
        try:
            import ezdxf
        except ImportError:
            return {}

        doc = ezdxf.readfile(str(reinf))
        msp = doc.modelspace()
        labs = self._extract_labels(msp)
        dims = self._extract_dimensions(msp)
        result: Dict[str, Tuple[float, float, List[str]]] = {}

        # Pre-count measurement frequency to reject global constants
        all_meas = [round(m, 0) for m, _, _ in dims]
        freq = Counter(all_meas)
        global_constant = None
        if all_meas:
            most, count = freq.most_common(1)[0]
            if count >= max(5, len(beams) // 3):
                global_constant = most

        for bid, pts in labs.items():
            # Prefer registry centroid if available
            rec = beams.get(bid, {})
            if rec.get("centroid_x") is not None:
                cx, cy = float(rec["centroid_x"]), float(rec["centroid_y"])
            else:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)

            near = []
            for meas, mx, my in dims:
                d = math.hypot(cx - mx, cy - my)
                if d <= 4500.0:
                    if global_constant is not None and round(meas, 0) == global_constant:
                        continue
                    near.append((d, meas))
            if not near:
                continue
            near.sort()
            # Prefer nearer dimensions; among top proximity band pick largest
            d0 = near[0][0]
            local = [t for t in near if t[0] <= d0 + 800][:10]
            best = max(local, key=lambda t: t[1])
            conf = max(0.30, 0.75 - best[0] / 6000.0)
            result[bid] = (
                best[1], conf,
                [f"reinf dim={best[1]:.1f} dist={best[0]:.1f}"],
            )
        return result

    @staticmethod
    def _extract_labels(msp) -> Dict[str, List[Tuple[float, float]]]:
        labs: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        pat = re.compile(r"^B\d{1,3}[A-Za-z]?$", re.I)
        for ent in msp.query("TEXT"):
            try:
                text = re.sub(r"%%[Uu]", "", ent.dxf.text or "").strip()
                m = re.match(r"^([A-Z]{1,3}\d{1,4}[A-Za-z]?)", text, re.I)
                if m and pat.match(m.group(1).upper()):
                    labs[m.group(1).upper()].append(
                        (float(ent.dxf.insert.x), float(ent.dxf.insert.y))
                    )
            except Exception:
                continue
        return labs

    @staticmethod
    def _extract_segments(msp) -> List[Tuple[float, float, float, float, float]]:
        segs = []
        for ent in msp.query("LINE"):
            try:
                s, t = ent.dxf.start, ent.dxf.end
                x1, y1, x2, y2 = float(s.x), float(s.y), float(t.x), float(t.y)
                length = math.hypot(x2 - x1, y2 - y1)
                if 1000 <= length <= 20000:
                    segs.append((length, x1, y1, x2, y2))
            except Exception:
                continue
        for ent in msp.query("LWPOLYLINE"):
            try:
                pts = list(ent.get_points("xy"))
                for i in range(len(pts) - 1):
                    x1, y1 = float(pts[i][0]), float(pts[i][1])
                    x2, y2 = float(pts[i + 1][0]), float(pts[i + 1][1])
                    length = math.hypot(x2 - x1, y2 - y1)
                    if 1000 <= length <= 20000:
                        segs.append((length, x1, y1, x2, y2))
            except Exception:
                continue
        return segs

    @staticmethod
    def _extract_dimensions(msp) -> List[Tuple[float, float, float]]:
        dims = []
        for ent in msp.query("DIMENSION"):
            try:
                meas = ent.dxf.get("actual_measurement", None)
                if meas is None:
                    continue
                meas = abs(float(meas))
                if not (1500 <= meas <= 15000):
                    continue
                pts = []
                for attr in ("defpoint", "defpoint2", "defpoint3", "text_midpoint"):
                    try:
                        pt = getattr(ent.dxf, attr, None)
                        if pt is not None:
                            pts.append((float(pt.x), float(pt.y)))
                    except Exception:
                        pass
                if not pts:
                    continue
                mx = sum(p[0] for p in pts) / len(pts)
                my = sum(p[1] for p in pts) / len(pts)
                dims.append((meas, mx, my))
            except Exception:
                continue
        return dims

    @staticmethod
    def _read_json(path: pathlib.Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
