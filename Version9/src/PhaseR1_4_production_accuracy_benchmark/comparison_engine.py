"""
Benchmark comparison — Official model vs Production snapshot.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from models import OfficialWorkbookModel, ProductionSnapshot
from terminology_mapper import map_official_description

MODEL_VERSION = "8.6.0"

# IS 1786 unit weights kg/m
_UNIT_WT = {8: 0.395, 10: 0.617, 12: 0.888, 16: 1.58, 20: 2.47, 25: 3.85, 32: 6.31}


def _role_family(role: str) -> str:
    r = (role or "").upper()
    if r.startswith("TOP_EXTRA"):
        return "TOP_EXTRA"
    if r.startswith("TOP"):
        return "TOP_MAIN"
    if r.startswith("BOTTOM_EXTRA"):
        return "BOTTOM_EXTRA"
    if r.startswith("BOTTOM"):
        return "BOTTOM_MAIN"
    if "HOOK" in r:
        return "STIRRUP_HOOK"
    if "STIRRUP" in r:
        return "STIRRUP"
    if "SPACER" in r:
        return "SPACER_BAR"
    if "SIDE" in r or r == "SFR" or "SIDE_FACE" in r:
        return "SIDE_FACE_REINFORCEMENT"
    return r or "UNKNOWN"


class ComparisonEngine:
    def compare(
        self,
        official: OfficialWorkbookModel,
        production: ProductionSnapshot,
    ) -> Dict[str, Any]:
        beam_acc = self._compare_beams(official, production)
        reinf_acc = self._compare_reinforcement(official, production)
        piece_acc = self._compare_pieces(official, production)
        ebar_acc = self._compare_engineering_bars(official, production)
        steel_acc = self._compare_steel(official, production)
        bbs_acc = self._compare_bbs(official, production)
        workbook_acc = self._compare_workbook(production)

        return {
            "model_version": MODEL_VERSION,
            "beam_accuracy": beam_acc,
            "reinforcement_accuracy": reinf_acc,
            "piece_accuracy": piece_acc,
            "engineeringbar_accuracy": ebar_acc,
            "steel_accuracy": steel_acc,
            "bbs_accuracy": bbs_acc,
            "workbook_accuracy": workbook_acc,
        }

    def _compare_beams(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        off_ids = {b.beam_id.upper() for b in official.beams}
        prod_ids = {b.beam_id.upper() for b in production.beams}
        if not prod_ids and production.engineering_bars:
            prod_ids = {str(b.get("beam_id") or "").upper() for b in production.engineering_bars if b.get("beam_id")}

        matched = sorted(off_ids & prod_ids)
        missing = sorted(off_ids - prod_ids)
        extra = sorted(prod_ids - off_ids)

        geometry: List[Dict[str, Any]] = []
        for bid in matched:
            ob = next(b for b in official.beams if b.beam_id.upper() == bid)
            pb = next((b for b in production.beams if b.beam_id.upper() == bid), None)
            geom = (pb.geometry if pb else {}) or {}
            span = geom.get("span_m") or geom.get("length_m") or geom.get("clear_span_m")
            length_ok = None
            if ob.length_m and span:
                length_ok = abs(float(ob.length_m) - float(span)) <= max(0.05, 0.02 * float(ob.length_m))
            geometry.append({
                "beam_id": bid,
                "official_length_m": ob.length_m,
                "production_span_m": span,
                "length_match": length_ok,
                "official_concrete_m3": ob.concrete_m3,
                "official_shuttering_m2": ob.shuttering_m2,
            })

        recall = len(matched) / len(off_ids) if off_ids else 0.0
        precision = len(matched) / len(prod_ids) if prod_ids else 0.0
        f1 = (2 * recall * precision / (recall + precision)) if (recall + precision) else 0.0
        geom_scores = [g["length_match"] for g in geometry if g["length_match"] is not None]
        geom_acc = (sum(1 for x in geom_scores if x) / len(geom_scores)) if geom_scores else 0.0

        return {
            "official_beam_count": len(off_ids),
            "production_beam_count": len(prod_ids),
            "matched": matched,
            "missing_beams": missing,
            "extra_beams": extra,
            "detection_recall": round(recall, 4),
            "detection_precision": round(precision, 4),
            "detection_f1": round(f1, 4),
            "geometry_accuracy": round(geom_acc, 4),
            "geometry_comparisons": geometry,
        }

    def _compare_reinforcement(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        off_by_beam: Dict[str, List] = defaultdict(list)
        for row in official.reinforcement_rows:
            off_by_beam[row.beam_id.upper()].append(row)

        prod_roles_by_beam: Dict[str, List[str]] = defaultdict(list)
        for bar in production.engineering_bars:
            bid = str(bar.get("beam_id") or "").upper()
            role = _role_family(str(bar.get("bar_role") or ""))
            if bid:
                prod_roles_by_beam[bid].append(role)
        # also intents
        for it in production.intents:
            bid = str(it.get("beam_id") or "").upper()
            role = _role_family(str(it.get("resolved_role") or it.get("role") or ""))
            if bid and role not in prod_roles_by_beam[bid]:
                prod_roles_by_beam[bid].append(role)

        class_matches = 0
        class_total = 0
        missing_rows = 0
        diameter_mismatches = 0
        details: List[Dict[str, Any]] = []

        for bid, rows in off_by_beam.items():
            prod_roles = list(prod_roles_by_beam.get(bid, []))
            used = set()
            for row in rows:
                class_total += 1
                role = row.role if row.role != "UNKNOWN" else map_official_description(row.description)
                found = False
                for i, pr in enumerate(prod_roles):
                    if i in used:
                        continue
                    if pr == role or (role == "STIRRUP_HOOK" and pr == "STIRRUP"):
                        used.add(i)
                        found = True
                        class_matches += 1
                        break
                if not found:
                    missing_rows += 1
                    details.append({
                        "beam_id": bid,
                        "description": row.description,
                        "role": role,
                        "status": "MISSING_OR_MISCLASSIFIED",
                    })

        # diameter check via bars
        for bar in production.engineering_bars:
            bid = str(bar.get("beam_id") or "").upper()
            dia = bar.get("diameter_mm")
            role = _role_family(str(bar.get("bar_role") or ""))
            off_rows = [r for r in off_by_beam.get(bid, []) if r.role == role]
            if off_rows and dia:
                if not any(
                    r.diameter and abs(float(r.diameter) - float(dia)) < 0.5
                    for r in off_rows
                ):
                    diameter_mismatches += 1

        cls_acc = class_matches / class_total if class_total else 0.0
        return {
            "official_row_count": class_total,
            "classification_matches": class_matches,
            "classification_accuracy": round(cls_acc, 4),
            "missing_reinforcement_rows": missing_rows,
            "diameter_mismatch_signals": diameter_mismatches,
            "sample_issues": details[:50],
        }

    def _compare_pieces(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        piece_count = len(production.pieces)
        if piece_count == 0:
            ps = (production.steel_summary or {}).get("piece_summary") or {}
            piece_count = int(ps.get("piece_count") or 0)
        off_rows = len(official.reinforcement_rows)
        # pieces can expand (zones / supports) — ratio informative, not equality
        ratio = piece_count / off_rows if off_rows else 0.0
        # score: presence + expansion in reasonable band
        if piece_count <= 0:
            score = 0.0
        elif 0.8 <= ratio <= 3.0:
            score = 0.85
        elif ratio > 0:
            score = 0.55
        else:
            score = 0.0
        return {
            "official_reinforcement_rows": off_rows,
            "production_pieces": piece_count,
            "piece_to_row_ratio": round(ratio, 4),
            "piece_generation_score": round(score, 4),
        }

    def _compare_engineering_bars(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        n_bars = len(production.engineering_bars)
        n_off = len(official.reinforcement_rows)
        beams_with_bars = len({str(b.get("beam_id")) for b in production.engineering_bars if b.get("beam_id")})
        off_beams = len(official.beams)
        coverage = beams_with_bars / off_beams if off_beams else 0.0
        # quantity score — bars should exist for matched beams
        if n_bars <= 0:
            score = 0.0
        elif coverage >= 0.9 and n_bars >= n_off * 0.5:
            score = 0.85
        elif coverage >= 0.5:
            score = 0.6
        else:
            score = 0.35
        return {
            "official_rows": n_off,
            "production_engineering_bars": n_bars,
            "beams_with_bars": beams_with_bars,
            "official_beams": off_beams,
            "beam_coverage": round(coverage, 4),
            "engineeringbar_score": round(score, 4),
        }

    def _compare_steel(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        off_kg = float(official.steel_summary.total_kg or 0.0)
        prod_kg = float((production.steel_summary or {}).get("total_kg") or 0.0)
        abs_diff = abs(off_kg - prod_kg)
        pct = (abs_diff / off_kg * 100.0) if off_kg > 0 else (100.0 if prod_kg > 0 else 0.0)
        # score: 100% at 0 diff, 0% at >=50% error
        score = max(0.0, 1.0 - min(pct, 50.0) / 50.0)

        dia_rows = []
        off_dia = official.steel_summary.diameter_summary or {}
        # convert official MT → kg for comparison when production diameter available
        prod_dia = (production.steel_summary or {}).get("diameter_kg") or {}
        dia_scores = []
        for d, mt in sorted(off_dia.items()):
            off_d_kg = float(mt) * 1000.0
            prod_d_kg = float(prod_dia.get(str(d)) or prod_dia.get(d) or 0.0)
            if off_d_kg <= 0 and prod_d_kg <= 0:
                continue
            d_pct = abs(off_d_kg - prod_d_kg) / off_d_kg * 100.0 if off_d_kg > 0 else 100.0
            d_score = max(0.0, 1.0 - min(d_pct, 50.0) / 50.0)
            dia_scores.append(d_score)
            dia_rows.append({
                "diameter_mm": d,
                "official_mt": mt,
                "official_kg": round(off_d_kg, 3),
                "production_kg": round(prod_d_kg, 3),
                "abs_diff_kg": round(abs(off_d_kg - prod_d_kg), 3),
                "pct_error": round(d_pct, 2),
                "score": round(d_score, 4),
            })

        # cut length: compare official cut lengths vs piece/bar cut lengths when available
        cut_scores = []
        pieces_by_beam_role: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        for pc in production.pieces:
            bid = str(pc.get("beam_id") or "").upper()
            role = _role_family(str(pc.get("piece_type") or pc.get("role") or ""))
            cl = pc.get("cut_length_mm")
            if bid and cl:
                pieces_by_beam_role[(bid, role)].append(float(cl) / 1000.0)
        # fallback: EngineeringBar metadata cut lengths
        if not pieces_by_beam_role:
            for bar in production.engineering_bars:
                bid = str(bar.get("beam_id") or "").upper()
                role = _role_family(str(bar.get("bar_role") or ""))
                meta = bar.get("engineering_metadata") or {}
                cl = meta.get("cut_length_mm")
                if bid and cl:
                    pieces_by_beam_role[(bid, role)].append(float(cl) / 1000.0)
        for row in official.reinforcement_rows:
            if not row.cut_length:
                continue
            key = (row.beam_id.upper(), row.role)
            cands = pieces_by_beam_role.get(key) or []
            if not cands:
                continue
            best = min(abs(c - float(row.cut_length)) for c in cands)
            ok = best <= max(0.05, 0.05 * float(row.cut_length))
            cut_scores.append(1.0 if ok else 0.0)

        cut_acc = sum(cut_scores) / len(cut_scores) if cut_scores else 0.0
        dia_acc = sum(dia_scores) / len(dia_scores) if dia_scores else score

        return {
            "official_total_kg": round(off_kg, 3),
            "official_total_mt": official.steel_summary.total_mt,
            "production_total_kg": round(prod_kg, 3),
            "abs_diff_kg": round(abs_diff, 3),
            "pct_error": round(pct, 2),
            "overall_steel_score": round(score, 4),
            "diameter_accuracy": round(dia_acc, 4),
            "diameter_rows": dia_rows,
            "cut_length_accuracy": round(cut_acc, 4),
            "cut_length_comparisons": len(cut_scores),
            "weight_accuracy": round(score, 4),
        }

    def _compare_bbs(
        self, official: OfficialWorkbookModel, production: ProductionSnapshot
    ) -> Dict[str, Any]:
        bbs_rows = int((production.bbs or {}).get("bbs_rows") or 0)
        beams_bbs = int((production.bbs or {}).get("beams_reaching_bbs") or 0)
        off_beams = len(official.beams)
        coverage = beams_bbs / off_beams if off_beams else 0.0
        # expect roughly >= official reinforcement rows (aggregation may reduce)
        row_ratio = bbs_rows / max(1, len(official.reinforcement_rows))
        if bbs_rows <= 0:
            score = 0.0
        elif coverage >= 0.9 and row_ratio >= 0.3:
            score = 0.8
        elif coverage >= 0.5:
            score = 0.55
        else:
            score = 0.3
        return {
            "bbs_rows": bbs_rows,
            "beams_reaching_bbs": beams_bbs,
            "official_beams": off_beams,
            "bbs_beam_coverage": round(coverage, 4),
            "bbs_score": round(score, 4),
        }

    def _compare_workbook(self, production: ProductionSnapshot) -> Dict[str, Any]:
        wb = production.workbook or {}
        exists = bool(wb.get("exists"))
        size = int(wb.get("size_bytes") or 0)
        score = 1.0 if exists and size > 1000 else (0.4 if exists else 0.0)
        return {
            "workbook_exists": exists,
            "workbook_path": wb.get("path"),
            "size_bytes": size,
            "workbook_score": round(score, 4),
        }
