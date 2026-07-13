"""Build Phase L.2.1 report payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from engineering_feature_model import EngineeringFeatureModel, MODEL_VERSION, PHASE


class FeatureReporting:
    @staticmethod
    def build_geometry_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._geom()}
                for f in features
            ],
        }

    @staticmethod
    def build_position_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._pos()}
                for f in features
            ],
        }

    @staticmethod
    def build_continuity_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._cont()}
                for f in features
            ],
        }

    @staticmethod
    def build_support_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._supp()}
                for f in features
            ],
        }

    @staticmethod
    def build_extent_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._ext()}
                for f in features
            ],
        }

    @staticmethod
    def build_orientation_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._ori()}
                for f in features
            ],
        }

    @staticmethod
    def build_annotation_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._ann()}
                for f in features
            ],
        }

    @staticmethod
    def build_topology_features(features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        return {
            "total": len(features),
            "features": [
                {"feature_id": f.feature_id, "bar_id": f.bar_id, "beam_id": f.beam_id,
                 **f._top()}
                for f in features
            ],
        }

    @staticmethod
    def build_summary(result: Dict[str, Any]) -> Dict[str, Any]:
        stats = result.get("statistics") or {}
        val = result.get("validation") or {}
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "validation_status": val.get("status"),
            "total_features": stats.get("total_features"),
            "total_beams": stats.get("total_beams"),
            "completeness_rate_percent": stats.get("completeness_rate_percent"),
            "zone_distribution": stats.get("zone_distribution"),
            "orientation_distribution": stats.get("orientation_distribution"),
            "extent_distribution": stats.get("extent_distribution"),
        }
