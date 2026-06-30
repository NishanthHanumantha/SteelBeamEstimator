"""Phase F — Framing Plan Intelligence (F.1–F.7) and G.1 runner."""

import _bootstrap  # noqa: F401

import argparse
import sys
from pathlib import Path

from loguru import logger

from src.config.output_paths import OutputPaths, OUTPUT_ROOT
from src.framing.beam_geometry_pipeline import BeamGeometryPipeline

DEFAULT_INPUT = Path("data/framing")
DEFAULT_CONFIG = Path("config/framing.yaml")


def configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase F (F.1–F.7) and Phase G.1 reinforcement loading.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=str(OUTPUT_ROOT),
        help="Output root (default: data/output)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT),
        help="Framing plan DXF file or directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help="Framing config YAML path",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    result = BeamGeometryPipeline(
        OutputPaths(Path(args.output_dir)),
        input_path=args.input,
        config_path=args.config,
    ).run()
    workspace_validation = result["workspace_validation"]
    reinforcement_validation = result.get("reinforcement_validation", {})
    drawing_identity_validation = result.get("drawing_identity_validation", {})
    drawing_set_validation = result.get("drawing_set_validation", {})
    drawing_set_state_validation = result.get("drawing_set_state_validation", {})
    reinforcement_drawing_validation = result.get("reinforcement_drawing_validation", {})
    model = result["model"]
    svc = model.get("engineering_services_registry", {})

    print("\n" + "=" * 52)
    print("PHASE F.7")
    print("Project Workspace & Engineering Services")
    print("=" * 52)
    print(f"Projects: {1 if model.get('project_workspace') else 0}")
    print(f"General Notes: {1 if model.get('project_workspace', {}).get('general_notes') else 0}")
    print(f"Floors: {model.get('floor_registry', {}).get('floor_count', 0)}")
    print(f"Beam Contexts: {len(model.get('beam_engineering_contexts', []))}")
    print(f"Engineering Services: {svc.get('service_count', 0)}")
    print(f"Validation: {workspace_validation['status']}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1")
    print("Floor Reinforcement Loading")
    print("=" * 52)
    reg = model.get("reinforcement_registry", {})
    print(f"Reinforcement Workspaces: {len(model.get('reinforcement_workspaces', []))}")
    print(f"Documents Loaded: {reg.get('document_count', 0)}")
    print(f"Validation: {reinforcement_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.1")
    print("Drawing Identity & Floor Detection")
    print("=" * 52)
    drawing_reg = model.get("drawing_registry", {})
    ws_mgr = model.get("workspace_manager", {})
    print(f"Drawings Identified: {drawing_reg.get('drawing_count', 0)}")
    print(f"Floor Source: {ws_mgr.get('floor_source', '?')}")
    floors = model.get("project_workspace", {}).get("floors", [])
    if floors:
        print(f"Detected Floor: {floors[0].get('floor_name', '?')} ({floors[0].get('floor_id', '?')})")
    print(f"Validation: {drawing_identity_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.2")
    print("Drawing Set Architecture")
    print("=" * 52)
    set_reg = model.get("drawing_set_registry", {})
    print(f"Drawing Sets: {set_reg.get('drawing_set_count', 0)}")
    for ds in model.get("drawing_sets", []):
        print(f"  {ds.get('drawing_set_id')} — {ds.get('floor_name')} ({ds.get('status')})")
    print(f"Validation: {drawing_set_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.1.3")
    print("Drawing Set Lifecycle & Beam Index")
    print("=" * 52)
    indices = model.get("beam_indices", [])
    total_beams = sum(i.get("beam_count", 0) for i in indices)
    print(f"Drawing Sets: {len(model.get('drawing_sets', []))}")
    print(f"Beams Indexed: {total_beams}")
    for ds in model.get("drawing_sets", []):
        ver = ds.get("drawing_set_version", {})
        print(
            f"  {ds.get('drawing_set_id')} v{ver.get('drawing_set_version', '?')} "
            f"loading={ds.get('loading_state', '?')}"
        )
    print(f"Validation: {drawing_set_state_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.2.2")
    print("Engineering Detail Classification & Multi-View Recognition")
    print("=" * 52)
    dm = model.get("reinforcement_drawing_model", {})
    regions = dm.get("regions", [])
    single = sum(1 for r in regions if r.get("detail_type") == "SINGLE_BEAM")
    multiview = sum(1 for r in regions if r.get("detail_type") == "MULTI_VIEW_SINGLE_BEAM")
    continuous = sum(1 for r in regions if r.get("detail_type") == "CONTINUOUS_MULTI_SPAN")
    print(f"Drawing Models: {len(model.get('reinforcement_drawing_models', []))}")
    print(f"Regions: {dm.get('region_count', 0)}")
    print(f"  SINGLE_BEAM: {single}")
    print(f"  MULTI_VIEW_SINGLE_BEAM: {multiview}")
    print(f"  CONTINUOUS_MULTI_SPAN: {continuous}")
    print(f"Detail Views: {dm.get('detail_view_count', 0)}")
    print(f"Sketches: {dm.get('sketch_count', 0)}")
    print(f"Text Objects: {dm.get('text_count', 0)}")
    print(f"Leaders: {dm.get('leader_count', 0)}")
    print(f"Blocks: {dm.get('block_count', 0)}")
    print(f"Relationships: {dm.get('relationship_count', 0)}")
    print(f"Validation: {reinforcement_drawing_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.2.3")
    print("Engineering Detail Context Layer")
    print("=" * 52)
    detail_context_validation = result.get("detail_context_validation", {})
    contexts = dm.get("detail_contexts", [])
    print(f"Detail Contexts: {dm.get('detail_context_count', 0)}")
    for ctx in contexts:
        marks = "/".join(ctx.get("beam_marks", []))
        print(
            f"  {ctx.get('detail_context_id')} — {ctx.get('detail_type')} "
            f"[{marks}] views={ctx.get('view_count', 0)}"
        )
    print(f"G.2.2 Validation: {reinforcement_drawing_validation.get('status', 'SKIP')}")
    print(f"G.2.3 Validation: {detail_context_validation.get('status', 'SKIP')}")
    print("=" * 52)

    print("\n" + "=" * 52)
    print("PHASE G.2.4")
    print("Engineering Detail Identity & Fingerprinting")
    print("=" * 52)
    detail_identity_validation = result.get("detail_identity_validation", {})
    identities = dm.get("detail_identities", [])
    fingerprints = dm.get("detail_fingerprints", [])
    print(f"Detail Identities: {dm.get('detail_identity_count', 0)}")
    print(f"Detail Fingerprints: {dm.get('detail_fingerprint_count', 0)}")
    status_counts: dict[str, int] = {}
    for ident in identities:
        ms = ident.get("matching_status", "?")
        status_counts[ms] = status_counts.get(ms, 0) + 1
        marks = ident.get("primary_beam_mark", "")
        sec = ident.get("secondary_beam_marks", [])
        if sec:
            marks += "/" + "/".join(sec)
        print(
            f"  {ident.get('detail_identity_id')} — {ident.get('detail_type')} "
            f"[{marks}] views={ident.get('view_count', 0)} "
            f"status={ms}"
        )
    print("Matching Status Summary:")
    for ms, count in sorted(status_counts.items()):
        print(f"  {ms}: {count}")
    if identities and fingerprints:
        sample_ident = next(
            (i for i in identities if i.get("detail_identity_id") == "DETAIL::008"),
            identities[0],
        )
        sample_fp = next(
            (
                f
                for f in fingerprints
                if f.get("detail_identity_id") == sample_ident.get("detail_identity_id")
            ),
            fingerprints[0],
        )
        print(f"\nSample Identity: {sample_ident.get('detail_identity_id')}")
        print(f"  primary={sample_ident.get('primary_beam_mark')} "
              f"secondary={sample_ident.get('secondary_beam_marks')}")
        print(f"Sample Fingerprint overall_hash: {str(sample_fp.get('overall_hash', ''))[:16]}...")
    print(f"G.2.4 Validation: {detail_identity_validation.get('status', 'SKIP')}")
    if detail_identity_validation.get("checks"):
        passed = sum(
            1 for c in detail_identity_validation["checks"] if c.get("status") == "PASS"
        )
        total = len(detail_identity_validation["checks"])
        print(f"  Checks: {passed}/{total} PASS")
    print("=" * 52 + "\n")

    print("\n" + "=" * 52)
    print("PHASE G.2.5")
    print("Beam Match Candidate Engine")
    print("=" * 52)
    beam_candidate_validation = result.get("beam_candidate_validation", {})
    candidates = dm.get("beam_match_candidates", [])
    print(f"Beam Match Candidates: {dm.get('beam_match_candidate_count', 0)}")
    state_counts: dict[str, int] = {}
    for ident in identities:
        ms = ident.get("matching_state", "?")
        state_counts[ms] = state_counts.get(ms, 0) + 1
    print("Matching State Summary:")
    for ms, count in sorted(state_counts.items()):
        print(f"  {ms}: {count}")
    for ident in identities:
        iid = ident.get("detail_identity_id", "")
        icands = [c for c in candidates if c.get("detail_identity_id") == iid]
        if not icands:
            continue
        marks = ident.get("primary_beam_mark", "")
        sec = ident.get("secondary_beam_marks", [])
        if sec:
            marks += "/" + "/".join(sec)
        cand_str = ", ".join(
            f"{c.get('beam_context_id')}({c.get('score', 0):.2f})" for c in icands
        )
        print(f"  {iid} [{marks}] -> {cand_str}")
    ranking = result.get("model", {}).get("beam_candidate_ranking", {})
    sample_rank = next(
        (r for r in ranking.get("rankings", []) if r.get("detail_identity_id") == "DETAIL::008"),
        ranking.get("rankings", [{}])[0] if ranking.get("rankings") else {},
    )
    if sample_rank:
        print(f"\nSample Ranking: {sample_rank.get('detail_identity_id')}")
        print(f"  best={sample_rank.get('best_candidate_id')}")
    if candidates:
        sample_cand = next(
            (c for c in candidates if c.get("detail_identity_id") == "DETAIL::001"),
            candidates[0],
        )
        print(f"Sample Candidate: {sample_cand.get('candidate_id')}")
        print(f"  beam={sample_cand.get('beam_context_id')} score={sample_cand.get('score')}")
    print(f"G.2.5 Validation: {beam_candidate_validation.get('status', 'SKIP')}")
    if beam_candidate_validation.get("checks"):
        passed = sum(
            1 for c in beam_candidate_validation["checks"] if c.get("status") == "PASS"
        )
        total = len(beam_candidate_validation["checks"])
        print(f"  Checks: {passed}/{total} PASS")
    print("=" * 52 + "\n")

    print("\n" + "=" * 52)
    print("PHASE G.2.6")
    print("Match Decision Layer")
    print("=" * 52)
    match_decision_validation = result.get("match_decision_validation", {})
    decisions = dm.get("match_decisions", [])
    print(f"Match Decisions: {dm.get('match_decision_count', 0)}")
    status_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    review_count = 0
    for decision in decisions:
        st = decision.get("decision_status", "?")
        status_counts[st] = status_counts.get(st, 0) + 1
        reason = decision.get("decision_reason", "?")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if decision.get("requires_manual_review"):
            review_count += 1
    print("Decision Status Summary:")
    for st, count in sorted(status_counts.items()):
        print(f"  {st}: {count}")
    print("Decision Reason Summary:")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")
    print(f"Manual Review Required: {review_count}/{len(decisions)}")
    sample_decision = next(
        (d for d in decisions if d.get("detail_identity_id") == "DETAIL::008"),
        decisions[0] if decisions else {},
    )
    if sample_decision:
        print(f"\nSample Decision: {sample_decision.get('decision_id')}")
        print(f"  recommended={sample_decision.get('recommended_candidate_id')}")
        print(f"  beam={sample_decision.get('recommended_beam_context_id')}")
        print(f"  reason={sample_decision.get('decision_reason')}")
        print(f"  confidence={sample_decision.get('confidence')}")
    print(f"G.2.6 Validation: {match_decision_validation.get('status', 'SKIP')}")
    if match_decision_validation.get("checks"):
        passed = sum(
            1 for c in match_decision_validation["checks"] if c.get("status") == "PASS"
        )
        total = len(match_decision_validation["checks"])
        print(f"  Checks: {passed}/{total} PASS")
    print("=" * 52 + "\n")

    print("\n" + "=" * 52)
    print("PHASE G.2.7")
    print("Match Decision Quality & Versioning")
    print("=" * 52)
    match_decision_quality_validation = result.get("match_decision_quality_validation", {})
    level_counts: dict[str, int] = {}
    quality_counts: dict[str, int] = {}
    for decision in decisions:
        level = decision.get("confidence_level", "?")
        level_counts[level] = level_counts.get(level, 0) + 1
        qstatus = decision.get("decision_quality", {}).get("quality_status", "?")
        quality_counts[qstatus] = quality_counts.get(qstatus, 0) + 1
    print("Confidence Level Summary:")
    for level, count in sorted(level_counts.items()):
        print(f"  {level}: {count}")
    print("Quality Status Summary:")
    for qstatus, count in sorted(quality_counts.items()):
        print(f"  {qstatus}: {count}")
    algo = result.get("model", {}).get("decision_algorithm", {})
    if algo.get("algorithms"):
        node = algo["algorithms"][0]
        print(f"\nAlgorithm: {node.get('name')} v{node.get('version')} ({node.get('family')})")
    sample = next(
        (d for d in decisions if d.get("detail_identity_id") == "DETAIL::008"),
        decisions[0] if decisions else {},
    )
    if sample:
        print(f"\nSample Decision Quality: {sample.get('decision_id')}")
        print(f"  confidence_level={sample.get('confidence_level')}")
        print(f"  quality_status={sample.get('decision_quality', {}).get('quality_status')}")
        print(f"  algorithm={sample.get('algorithm_info', {}).get('algorithm_name')} "
              f"v{sample.get('algorithm_info', {}).get('algorithm_version')}")
    print(f"G.2.7 Validation: {match_decision_quality_validation.get('status', 'SKIP')}")
    if match_decision_quality_validation.get("checks"):
        passed = sum(
            1 for c in match_decision_quality_validation["checks"] if c.get("status") == "PASS"
        )
        total = len(match_decision_quality_validation["checks"])
        print(f"  Checks: {passed}/{total} PASS")
    print("=" * 52 + "\n")

    failed = any(
        result[k]["status"] == "FAIL"
        for k in (
            "f1_validation",
            "dimension_validation",
            "support_validation",
            "section_validation",
            "length_validation",
            "graph_validation",
            "context_validation",
            "workspace_validation",
        )
    )
    if reinforcement_validation.get("status") == "FAIL":
        failed = True
    if drawing_identity_validation.get("status") == "FAIL":
        failed = True
    if drawing_set_validation.get("status") == "FAIL":
        failed = True
    if drawing_set_state_validation.get("status") == "FAIL":
        failed = True
    if reinforcement_drawing_validation.get("status") == "FAIL":
        failed = True
    if result.get("detail_context_validation", {}).get("status") == "FAIL":
        failed = True
    if result.get("detail_identity_validation", {}).get("status") == "FAIL":
        failed = True
    if result.get("beam_candidate_validation", {}).get("status") == "FAIL":
        failed = True
    if result.get("match_decision_validation", {}).get("status") == "FAIL":
        failed = True
    if result.get("match_decision_quality_validation", {}).get("status") == "FAIL":
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
