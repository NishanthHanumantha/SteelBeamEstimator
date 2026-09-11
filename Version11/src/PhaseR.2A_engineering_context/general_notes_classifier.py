"""
General Notes Classifier.

Groups text items from the GN DXF into engineering topic buckets so that
downstream parsers can operate on pre-filtered item sets.
"""
from __future__ import annotations
import re
from typing import Dict, List

from .general_notes_text_extractor import DXFTextItem, GeneralNotesTextExtractor


# Topic detection patterns
_TOPIC_PATTERNS = {
    "development_length": re.compile(r"development|anchorage|LD\s+FOR|FY[-\s]?\d+", re.I),
    "cover":              re.compile(r"cover|TABLE\s+2|clear\s+cover|nominal\s+cover", re.I),
    "steel_grade":        re.compile(r"\bFe\s*\d{3}\b|\bFY[-\s]?\d+\b|\bHYSD\b", re.I),
    "concrete_grade":     re.compile(r"\bM(20|25|30|35|40)\b"),
    "hook_bend":          re.compile(r"hook|bend|4xdb|5xdb|\d+\s*xdb|standard\s+9[05]", re.I),
    "lap_splice":         re.compile(r"lap|splice|lapped", re.I),
    "spacer":             re.compile(r"spacer|cover\s+block|chair", re.I),
    "is_code":            re.compile(r"IS\s*456|IS\s*2502|IS\s*16172|SP\s*34|IS\s*\d{3,}", re.I),
    "materials":          re.compile(r"CEMENT|AGGREGATE|ADMIXTURE|RMC|MIX\s+DESIGN|OPC|GGBS", re.I),
    "general_notes":      re.compile(r"dimensions.*SI\s+units|figured|work\s+to", re.I),
}


class GeneralNotesClassifier:
    """
    Classifies text items by engineering topic.
    A single item may appear in multiple topics.
    """

    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def classify(self) -> Dict[str, List[DXFTextItem]]:
        """
        Returns dict: topic_name -> [DXFTextItem, ...]
        """
        all_items = self._ext.extract()
        result: Dict[str, List[DXFTextItem]] = {t: [] for t in _TOPIC_PATTERNS}

        for item in all_items:
            for topic, pattern in _TOPIC_PATTERNS.items():
                if pattern.search(item.text):
                    result[topic].append(item)

        return result

    def summary(self) -> Dict[str, int]:
        classified = self.classify()
        return {topic: len(items) for topic, items in classified.items()}
