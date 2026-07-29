"""
Generate focused engineering review questions.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from beam_analysis_model import MODEL_VERSION


class ReviewQuestionGenerator:
    def generate(self, statistics: Dict[str, Any], pattern: Dict[str, Any]) -> Dict[str, Any]:
        questions = [
            {
                "id": "Q01",
                "question": "Why was the stirrup not detected for the majority of missing beams?",
                "focus": "Annotation Discovery",
            },
            {
                "id": "Q02",
                "question": "Is the stirrup notation used on missing beams a supported estimator convention?",
                "focus": "Notation",
            },
            {
                "id": "Q03",
                "question": "Is another annotation (typical detail / schedule / section callout) intended to supply stirrups for missing beams?",
                "focus": "Inheritance",
            },
            {
                "id": "Q04",
                "question": "Does any beam inherit stirrups from another view or typical stirrup detail?",
                "focus": "Inheritance",
            },
            {
                "id": "Q05",
                "question": "Are leaders correctly associated to beam marks for missing stirrup cases?",
                "focus": "Leader association",
            },
            {
                "id": "Q06",
                "question": "Is multi-zone stirrup notation (e.g. 100/200/100) written differently on missing beams?",
                "focus": "Notation",
            },
            {
                "id": "Q07",
                "question": "Does another drawing (framing / schedule / typical details) define stirrups for these beams?",
                "focus": "Multi-drawing",
            },
            {
                "id": "Q08",
                "question": "Can multiple beams share one stirrup annotation?",
                "focus": "Shared annotation",
            },
            {
                "id": "Q09",
                "question": "Are section views mandatory for stirrup interpretation on this project?",
                "focus": "Section views",
            },
            {
                "id": "Q10",
                "question": "What does the annotation text 'TYPICAL STIRRUP DETAILS' mean for beams where it appears (e.g. B56)?",
                "focus": "Typical details",
            },
            {
                "id": "Q11",
                "question": "Should UNKNOWN annotations such as RC-UPSTAND be ignored for stirrup discovery?",
                "focus": "Noise filtering",
            },
            {
                "id": "Q12",
                "question": "For beams with TOP/BOTTOM bars but no STIRRUP role, is the stirrup omitted on the drawing or only omitted from association?",
                "focus": "Drawing completeness",
            },
            {
                "id": "Q13",
                "question": "Is stirrup diameter/spacing sometimes shown only as a schedule note rather than a beam callout?",
                "focus": "Schedule",
            },
            {
                "id": "Q14",
                "question": "Do detected beams (13) use a notation family that missing beams do not use?",
                "focus": "Notation family",
            },
            {
                "id": "Q15",
                "question": "Are C-hooks expected whenever stirrups exist, and should missing hooks be reviewed with missing stirrups?",
                "focus": "Hooks",
            },
            {
                "id": "Q16",
                "question": "Is beam orientation expected to affect stirrup annotation placement or discovery?",
                "focus": "Orientation",
            },
            {
                "id": "Q17",
                "question": "Should estimator practice assume a default stirrup when none is shown on the reinforcement drawing?",
                "focus": "Estimator convention",
            },
            {
                "id": "Q18",
                "question": "Which layers should be treated as authoritative for stirrup text on this drawing set?",
                "focus": "Layers",
            },
            {
                "id": "Q19",
                "question": "For RULE-012 failures, is Annotation Discovery the agreed first engineering investigation focus?",
                "focus": "Process",
            },
            {
                "id": "Q20",
                "question": "What evidence would the Estimation Team need in the next meeting to confirm root cause per beam?",
                "focus": "Review process",
            },
        ]
        return {
            "model_version": MODEL_VERSION,
            "question_count": len(questions),
            "context": {
                "coverage_pct": statistics.get("coverage_pct"),
                "detected_beams": statistics.get("detected_beams"),
                "missing_beams": statistics.get("missing_beams"),
                "pattern_conclusion": pattern.get("pattern_conclusion"),
            },
            "questions": questions,
        }
