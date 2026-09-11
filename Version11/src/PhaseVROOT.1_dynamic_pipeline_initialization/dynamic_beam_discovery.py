"""
Phase V.ROOT.1 -- dynamic_beam_discovery.py
PRIMARY MODULE: Dynamically discover ALL beams from any DXF drawing.

No beam IDs are hardcoded.
No Benchmark Set 1 assumptions.
Supports unlimited beam counts with any naming convention.

MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import math
import pathlib
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Beam label detection patterns (ordered most-specific -> least-specific)
# ---------------------------------------------------------------------------
_LABEL_PATTERNS: List[re.Pattern] = [
    re.compile(r'^B\d{1,3}[A-Za-z]?$'),               # B1, B2, B18, B1A
    re.compile(r'^B-\d{1,3}[A-Za-z]?$'),              # B-1, B-18
    re.compile(r'^GB[-_]?\d{1,3}[A-Za-z]?$', re.I),  # GB01, GB-01
    re.compile(r'^BM[-_]?\d{1,3}[A-Za-z]?$', re.I),  # BM01, BM-01
    re.compile(r'^RB[-_]?\d{1,3}[A-Za-z]?$', re.I),  # RB01, RB-01
    re.compile(r'^[A-Z]{1,3}[-_]?\d{1,4}[A-Za-z]?$'),  # Generic alphanumeric
]

# Patterns that EXCLUDE a text from being a beam label
_EXCLUDE_PATTERNS: List[re.Pattern] = [
    re.compile(r'^\d+[YTRyr]\d+'),        # 2Y16, 3T20 -- bar designations
    re.compile(r'^[YTRyr]\d+[@\-]\d+'),   # T10@150, T10-150
    re.compile(r'^\d+\.\d+$'),            # pure floats
    re.compile(r'^[\d.]+$'),              # pure numbers
    re.compile(r'^(TYP|NTS|EXP|RHS|SHS|UB|UC|CHS|EA)', re.I),
    re.compile(r'^(GL|EL|FL|RL|FFL|SFL|RFL)', re.I),
    re.compile(r'^(TOP|BOT|MID|CL|NA|TOS|BOS|SIDE)', re.I),
    re.compile(r'^(LINK|STIRRUP|HOOP|TIE|SHEAR|MAIN)', re.I),
    re.compile(r'^(NOTE|REF|DWG|DRG|SHEET|SH\.|FIG|FIGURE)', re.I),
    re.compile(r'^(CONC|CONCRETE|STEEL|REBAR|REINF)', re.I),
    re.compile(r'^(SPAN|WIDTH|DEPTH|HEIGHT|LENGTH)', re.I),
    re.compile(r'[@%/#&]'),               # contains special chars
    re.compile(r'\s{2,}'),               # multiple spaces (multiline text)
]

# Section size patterns: 200x600, 200X600, (200x600), 200*600
_SECTION_RE = re.compile(r'(\d{2,4})\s*[xX\u00d7*]\s*(\d{2,4})')

# Span dimension patterns: e.g. 5570, 4280 (in mm -- 3 to 5 digits)
_SPAN_RE = re.compile(r'\b(\d{3,5})\b')


def _is_beam_label(text: str) -> bool:
    """Return True if text matches a beam label pattern."""
    t = text.strip()
    if not t or len(t) < 2 or len(t) > 12:
        return False
    # Reject excluded patterns
    for exc in _EXCLUDE_PATTERNS:
        if exc.search(t):
            return False
    # Must match at least one label pattern
    for pat in _LABEL_PATTERNS:
        if pat.match(t):
            return True
    return False


def _extract_section(texts: List[str]) -> Tuple[Optional[float], Optional[float]]:
    """Extract width x depth from a list of nearby annotation texts."""
    for t in texts:
        m = _SECTION_RE.search(t)
        if m:
            w, d = float(m.group(1)), float(m.group(2))
            # Heuristic: width < depth for beams (common for 200x600)
            if d >= w:
                return w, d
            else:
                return d, w  # swap if reversed
    return None, None


def _extract_span(texts: List[str], exclude: List[str]) -> Optional[float]:
    """
    Extract a likely span value (1500-15000 mm) from nearby annotation texts.

    Prefer DIMENSION measurements over bare numeric text. Never select a
    global drawing-wide maximum — callers must pass spatially filtered texts.
    """
    dim_candidates: List[float] = []
    text_candidates: List[float] = []
    for t in texts:
        if t in exclude:
            continue
        # Positioned records may arrive as "DIM:8775.2"
        if isinstance(t, str) and t.startswith("DIM:"):
            try:
                val = float(t.split(":", 1)[1])
                if 1500.0 <= val <= 15000.0:
                    dim_candidates.append(val)
            except Exception:
                pass
            continue
        for m in _SPAN_RE.finditer(t):
            val = float(m.group(1))
            if 1500.0 <= val <= 15000.0:
                text_candidates.append(val)
    pool = dim_candidates or text_candidates
    if not pool:
        return None
    # Among local candidates choose the largest (typical clear-span dimension)
    return max(pool)


def _cluster_labels(
    labels: List[Dict[str, Any]],
    radius: float = 500.0,
) -> List[List[Dict[str, Any]]]:
    """
    Group label occurrences by spatial proximity.
    Returns a list of clusters (each cluster = related instances of one beam).
    """
    if not labels:
        return []
    clusters: List[List[Dict[str, Any]]] = []
    used = [False] * len(labels)

    for i, lb in enumerate(labels):
        if used[i]:
            continue
        cluster = [lb]
        used[i] = True
        for j, other in enumerate(labels):
            if used[j] or i == j:
                continue
            dx = lb['x'] - other['x']
            dy = lb['y'] - other['y']
            if math.hypot(dx, dy) <= radius:
                cluster.append(other)
                used[j] = True
        clusters.append(cluster)
    return clusters


class DynamicBeamDiscovery:
    """
    Parse a DXF beam reinforcement drawing and dynamically discover all beams.

    Supports:
      - Any beam naming convention (B1, GB-01, BM305, ...)
      - Unlimited beam counts
      - Automatic section geometry extraction
      - Automatic span estimation from dimension annotations
    """

    def __init__(self, cluster_radius: float = 500.0) -> None:
        self._cluster_radius = cluster_radius

    def discover(
        self, dxf_path: pathlib.Path
    ) -> Dict[str, Any]:
        """
        Parse the DXF file and return a discovery result dict.
        """
        t0 = time.perf_counter()

        try:
            import ezdxf  # type: ignore
        except ImportError:
            return self._fallback_result(dxf_path, "ezdxf not installed")

        try:
            doc = ezdxf.readfile(str(dxf_path))
        except Exception as exc:
            return self._fallback_result(dxf_path, str(exc))

        msp    = doc.modelspace()
        labels = self._extract_labels(msp)
        all_texts = self._extract_all_texts(msp)  # positioned records

        clusters  = _cluster_labels(labels, self._cluster_radius)
        beams     = self._build_beams(clusters, all_texts)
        beams     = self._reject_constant_span(beams)

        elapsed = round(time.perf_counter() - t0, 2)
        return {
            'dxf_path':          str(dxf_path),
            'dxf_stem':          dxf_path.stem,
            'beam_count':        len(beams),
            'total_text_entities': len(all_texts),
            'label_entities':    len(labels),
            'cluster_count':     len(clusters),
            'elapsed_s':         elapsed,
            'beams':             beams,
            'raw_labels':        [l['text'] for l in labels],
            'error':             None,
        }

    # ------------------------------------------------------------------
    def _extract_labels(self, msp: Any) -> List[Dict[str, Any]]:
        """
        Extract all text entities that look like beam labels.

        Handles:
          - Plain TEXT:  'B1', 'B-1', 'GB01'
          - %%U TEXT:    '%%UB1(200X750)-INV'   (DXF underline toggle)
          - MTEXT:       '{\\fArial;B1}', plain beam labels
        """
        labels: List[Dict[str, Any]] = []

        # TEXT entities (primary source for beam labels in many DXF workflows)
        for ent in msp.query('TEXT'):
            try:
                raw  = (ent.dxf.text or '').strip()
                ins  = ent.dxf.insert
                h    = float(getattr(ent.dxf, 'height', 2.5))

                # Strategy A: strip %%U (underline) and extract beam label
                # Pattern: %%UB1(200X750)-INV  ->  beam_id=B1, section=200x750
                cleaned_text = self._clean_text_entity(raw)
                # Try extracting beam-label from annotated form first
                annotated = self._extract_annotated_beam(raw, ins, h)
                if annotated:
                    labels.append(annotated)
                    continue

                # Strategy B: plain beam label
                if _is_beam_label(cleaned_text):
                    labels.append({
                        'text': cleaned_text.upper(),
                        'x':    float(ins.x),
                        'y':    float(ins.y),
                        'h':    h,
                        '_section_hint': None,
                    })
            except Exception:
                continue

        # MTEXT entities
        for ent in msp.query('MTEXT'):
            try:
                raw = ent.plain_mtext() if hasattr(ent, 'plain_mtext') else (ent.text or '')
                ins = ent.dxf.insert
                h   = float(getattr(ent.dxf, 'char_height', 2.5))
                for line in raw.splitlines():
                    text = self._clean_mtext(line.strip())
                    if _is_beam_label(text):
                        labels.append({
                            'text': text.upper(),
                            'x':    float(ins.x),
                            'y':    float(ins.y),
                            'h':    h,
                            '_section_hint': None,
                        })
            except Exception:
                continue

        return labels

    @staticmethod
    def _clean_text_entity(raw: str) -> str:
        """
        Strip DXF TEXT entity special codes (%%U, %%O, %%D, etc.)
        and return a clean string.
        """
        text = re.sub(r'%%[UuOoDdPp]', '', raw)   # underline, overline, degree, plus/minus
        text = re.sub(r'%%C', 'dia', text)          # circle/diameter symbol
        text = text.strip()
        return text

    @staticmethod
    def _extract_annotated_beam(raw: str, ins: Any, h: float) -> dict | None:
        """
        Parse annotated TEXT like '%%UB1(200X750)-INV' into a label record.
        Returns None if the pattern does not match.
        """
        # Strip %%U prefix(es)
        stripped = re.sub(r'%%[Uu]', '', raw).strip()

        # Pattern: <BEAM_ID>(<WIDTH>X<DEPTH>)[optional suffix]
        # e.g. B1(200X750)-INV  B14A(200X750)  B15(200~300X500)
        m = re.match(
            r'^([A-Z]{1,3}\d{1,4}[A-Za-z]?)\s*\(([^)]+)\)',
            stripped,
            re.IGNORECASE,
        )
        if not m:
            # Also try without parentheses: B1 alone
            m2 = re.match(r'^([A-Z]{1,3}\d{1,4}[A-Za-z]?)$', stripped, re.IGNORECASE)
            if m2 and _is_beam_label(m2.group(1)):
                return {
                    'text': m2.group(1).upper(),
                    'x': float(ins.x),
                    'y': float(ins.y),
                    'h': h,
                    '_section_hint': None,
                }
            return None

        beam_id  = m.group(1).upper()
        sec_text = m.group(2)   # e.g. '200X750' or '200~300X500'

        # Validate as beam label
        if not _is_beam_label(beam_id):
            return None

        # Extract section from parenthesised annotation
        # Handle variable depth: 200~300X500 -> take average for width, use depth
        sec_text_norm = re.sub(r'\d+~(\d+)', r'\1', sec_text)  # take upper bound
        sec_m = re.search(r'(\d+)\s*[xX]\s*(\d+)', sec_text_norm)
        section_hint = None
        if sec_m:
            w, d = float(sec_m.group(1)), float(sec_m.group(2))
            section_hint = {'width_mm': min(w, d), 'depth_mm': max(w, d), 'inferred': False}

        return {
            'text': beam_id,
            'x':    float(ins.x),
            'y':    float(ins.y),
            'h':    h,
            '_section_hint': section_hint,
        }

    def _extract_all_texts(self, msp: Any) -> List[Dict[str, Any]]:
        """
        Extract every text/dimension with its DXF position for spatial filtering.

        Returns list of records:
          {text, x, y, kind: 'TEXT'|'DIMENSION', measurement: Optional[float]}
        """
        records: List[Dict[str, Any]] = []
        for ent in msp.query('TEXT MTEXT'):
            try:
                if ent.dxftype() == 'MTEXT':
                    raw = ent.plain_mtext() if hasattr(ent, 'plain_mtext') else ''
                    cleaned = self._clean_mtext(raw).strip()
                    ins = ent.dxf.insert
                else:
                    raw = ent.dxf.text or ''
                    cleaned = self._clean_text_entity(raw).strip()
                    ins = ent.dxf.insert
                if cleaned:
                    records.append({
                        'text': cleaned,
                        'x': float(ins.x),
                        'y': float(ins.y),
                        'kind': 'TEXT',
                        'measurement': None,
                    })
            except Exception:
                continue
        for ent in msp.query('DIMENSION'):
            try:
                meas = ent.dxf.get('actual_measurement', None)
                meas_f = abs(float(meas)) if meas is not None else None
                pts = []
                for attr in ('defpoint', 'defpoint2', 'defpoint3', 'text_midpoint'):
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
                mtext = (ent.dxf.get('text', '') or '').strip()
                if mtext:
                    records.append({
                        'text': mtext,
                        'x': mx, 'y': my,
                        'kind': 'DIMENSION',
                        'measurement': meas_f,
                    })
                if meas_f is not None:
                    records.append({
                        'text': f'DIM:{round(meas_f, 1)}',
                        'x': mx, 'y': my,
                        'kind': 'DIMENSION',
                        'measurement': meas_f,
                    })
            except Exception:
                continue
        return records

    @staticmethod
    def _clean_mtext(raw: str) -> str:
        """Strip DXF MTEXT formatting codes."""
        # Remove {\...} formatting groups
        text = re.sub(r'\{\\[^;]+;', '', raw)
        text = re.sub(r'\}', '', text)
        # Remove \P (paragraph), \n, \t
        text = re.sub(r'\\[PnptT]', ' ', text)
        # Remove \L, \l (underline), \O, \o (overline)
        text = re.sub(r'\\[LOlo]', '', text)
        # Remove formatting like \fArial|b0|i0;
        text = re.sub(r'\\f[^;]+;', '', text)
        # Remove \H (height), \W (width), \Q (oblique)
        text = re.sub(r'\\[HWQ][\d.]+[x;]?', '', text)
        # Remove \S stacking
        text = re.sub(r'\\S[^;]+;', '', text)
        return text.strip()

    def _build_beams(
        self,
        clusters: List[List[Dict[str, Any]]],
        all_texts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build a beam record for each unique label cluster."""
        seen: Dict[str, Dict[str, Any]] = {}

        for cluster in clusters:
            if not cluster:
                continue
            labels_in_cluster = [c['text'] for c in cluster]
            label = max(set(labels_in_cluster), key=labels_in_cluster.count)

            cx = sum(c['x'] for c in cluster) / len(cluster)
            cy = sum(c['y'] for c in cluster) / len(cluster)

            if label in seen:
                existing = seen[label]
                existing['occurrence_count'] += len(cluster)
                existing['bbox']['x_min'] = min(existing['bbox']['x_min'], min(c['x'] for c in cluster))
                existing['bbox']['x_max'] = max(existing['bbox']['x_max'], max(c['x'] for c in cluster))
                existing['bbox']['y_min'] = min(existing['bbox']['y_min'], min(c['y'] for c in cluster))
                existing['bbox']['y_max'] = max(existing['bbox']['y_max'], max(c['y'] for c in cluster))
                continue

            # Use embedded section hint from annotated label (e.g. B1(200X750))
            section_hints = [c.get('_section_hint') for c in cluster if c.get('_section_hint')]
            if section_hints:
                sh = section_hints[0]
                width_mm  = sh.get('width_mm')
                depth_mm  = sh.get('depth_mm')
                inferred  = sh.get('inferred', False)
            else:
                nearby   = self._nearby_texts(cx, cy, all_texts, radius=600.0)
                width_mm, depth_mm = _extract_section(nearby)
                inferred = width_mm is None

            # Span search uses a larger adaptive radius (detail drawings place
            # clear-span dimensions farther from the beam mark than section notes)
            nearby_span = self._nearby_texts(cx, cy, all_texts, radius=2500.0)
            span_mm = _extract_span(nearby_span, [label])
            nearby = self._nearby_texts(cx, cy, all_texts, radius=600.0)

            seen[label] = {
                'beam_id':        label,
                'beam_mark':      label,
                'uuid':           str(uuid.uuid4()),
                'occurrence_count': len(cluster),
                'centroid_x':     round(cx, 2),
                'centroid_y':     round(cy, 2),
                'bbox': {
                    'x_min': min(c['x'] for c in cluster),
                    'x_max': max(c['x'] for c in cluster),
                    'y_min': min(c['y'] for c in cluster),
                    'y_max': max(c['y'] for c in cluster),
                },
                'section': {
                    'width_mm':  width_mm or 200.0,
                    'depth_mm':  depth_mm or 600.0,
                    'inferred':  inferred,
                },
                'clear_span_mm':    span_mm,
                'annotation_count': len(nearby),
                'status':           'DISCOVERED',
            }

        # Sort beam IDs naturally (B1, B2, ..., B10, B11, ... GB01, ...)
        def _natural_key(beam: Dict[str, Any]) -> tuple:
            bid = beam['beam_id']
            prefix = re.sub(r'\d', '', bid)
            nums   = re.findall(r'\d+', bid)
            num    = int(nums[0]) if nums else 0
            return (prefix, num)

        return sorted(seen.values(), key=_natural_key)

    def _nearby_texts(
        self,
        cx: float,
        cy: float,
        all_texts: List[Dict[str, Any]],
        radius: float = 600.0,
    ) -> List[str]:
        """Return text strings whose DXF position is within radius of (cx, cy)."""
        if not all_texts:
            return []
        # Backward-compatible: plain string list (legacy callers)
        if isinstance(all_texts[0], str):
            return list(all_texts)

        nearby: List[str] = []
        for rec in all_texts:
            try:
                dx = float(rec.get('x', 0)) - cx
                dy = float(rec.get('y', 0)) - cy
                if math.hypot(dx, dy) <= radius:
                    nearby.append(str(rec.get('text', '')))
            except Exception:
                continue
        return nearby

    @staticmethod
    def _reject_constant_span(beams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        If the majority of beams share an identical span, that value is almost
        certainly a global drawing-wide dimension wrongly assigned to every beam.
        Clear those spans so GeometryProvider can re-resolve them.
        """
        if len(beams) < 3:
            return beams
        from collections import Counter
        spans = [b.get('clear_span_mm') for b in beams if b.get('clear_span_mm')]
        if not spans:
            return beams
        rounded = [round(float(s), 0) for s in spans]
        most_common, count = Counter(rounded).most_common(1)[0]
        if count / len(beams) >= 0.5:
            for b in beams:
                s = b.get('clear_span_mm')
                if s is not None and round(float(s), 0) == most_common:
                    b['clear_span_mm'] = None
                    b['span_rejected_constant'] = True
                    b['span_rejected_value'] = most_common
        return beams

    @staticmethod
    def _fallback_result(dxf_path: pathlib.Path, error: str) -> Dict[str, Any]:
        return {
            'dxf_path':          str(dxf_path),
            'dxf_stem':          dxf_path.stem,
            'beam_count':        0,
            'total_text_entities': 0,
            'label_entities':    0,
            'cluster_count':     0,
            'elapsed_s':         0.0,
            'beams':             [],
            'raw_labels':        [],
            'error':             error,
        }
