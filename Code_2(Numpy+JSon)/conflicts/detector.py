"""
Conflict detection between retrieved chunks.

Extracts comparable policy facts ("Maximum password age: 90 days",
"Minimum length: 12 characters", ...) from each retrieved chunk and
groups them by normalized topic. When the same topic carries different
values from different chunks, a conflict is raised.

Design notes:
- Extraction is line-based and deliberately high-precision: only
  labeled facts ("Label: ...number...") and a small set of recurring
  phrasings ("changed every N days", "triage within N minutes") become
  claims. Silent false positives are worse than a few missed pairings -
  a conflict system that cries wolf gets ignored.
- The corpus versions are written with parallel bullet structure, so
  identical labels appear across versions; that is what makes the
  planted contradictions (90 vs 60 days, 8 vs 12 characters, ...)
  detectable deterministically.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """A single extracted policy fact tied to its source chunk."""
    topic: str                 # normalized label, e.g. "maximum password age"
    value: str                 # normalized value, e.g. "90 days"
    line: str                  # the original line the claim came from
    doc_id: str
    version: str
    effective_from: Optional[str]
    effective_to: Optional[str]
    is_current: bool
    score: float = 0.0
    chunk_id: str = ""

    def source_label(self) -> str:
        """Human-readable source reference, e.g. 'password-policy v3.0 (current)'."""
        status = "current" if self.is_current else "superseded"
        return f"{self.doc_id} {self.version} ({status})"


@dataclass
class Conflict:
    """Same topic, different values found across retrieved chunks."""
    topic: str
    claims: List[Claim] = field(default_factory=list)
    kind: str = "intra_document"   # or "cross_document"

    def values(self):
        """Distinct values in first-seen order, each with its claims."""
        ordered = []
        for claim in self.claims:
            for value, bucket in ordered:
                if value == claim.value:
                    bucket.append(claim)
                    break
            else:
                ordered.append((claim.value, [claim]))
        return ordered


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------

# "Label: value" bullets, e.g. "- Maximum password age: 90 days" or
# "- Password history: Remember last 5 passwords (increased from 10)".
# The label must not contain a dash or a second colon (so lines like
# "- Short-term: Isolate..." don't split in the wrong place) and the
# value must contain a digit. Trailing parentheticals such as
# "(increased from 10)" are stripped so the CURRENT value survives.
_LABELED_FACT_RE = re.compile(
    r"^\s*[-*]?\s*(?P<label>[A-Za-z][^:\-]{2,79}):\s*(?P<value>[^()]*\d[^()]*)"
    r"(?:\s*\([^)]*\))?\s*$"
)

# First "number unit" (or bare number) inside a value string. The unit is
# a single word - this keeps "ext. 5555, or ticketing" from becoming
# "5555 or" (or/and/via are not units and are dropped in normalization).
_NUMBER_UNIT_RE = re.compile(
    r"(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>[a-zA-Z%]+)?"
)

# Words that never continue a unit.
_NOT_UNITS = {"or", "and", "of", "to", "the", "a", "an", "in", "on", "at",
              "is", "are", "if", "with", "for"}

# Recurring-interval phrasings without a colon label, e.g.
# "- Passwords must be changed every 90 days" / "- Internal updates every 4 hours".
_EVERY_RE = re.compile(
    r"^\s*[-*]?\s*(?P<label>[A-Za-z][^:\-]{2,79}?\b(?:chang|rotat|replac|renew|updat)[a-z]*\s+every)\s+"
    r"(?P<num>\d[\d,]*)\s*(?P<unit>[a-zA-Z]+)\b",
    re.I,
)

# Deadline phrasings, e.g. "- Initial triage within 15 minutes of report".
_WITHIN_RE = re.compile(
    r"^\s*[-*]?\s*(?P<label>[A-Za-z][^:\-]{2,60}?)\s+within\s+"
    r"(?P<num>\d[\d,]*)\s*(?P<unit>minutes?|hours?|days?|weeks?|months?|years?"
    r"|\s?business\s+days?)\b",
    re.I,
)

_STOPWORDS = {"the", "a", "an", "of", "for", "and", "to"}


def _normalize_topic(label: str) -> str:
    """Normalize a label into a stable topic key."""
    words = re.sub(r"[^\w\s]", " ", label.lower()).split()
    return " ".join(w for w in words if w not in _STOPWORDS)


def _normalize_value(num: str, unit: Optional[str]) -> str:
    """Normalize a value: '1,000 Words' -> '1000 words'; bare '5' stays '5'."""
    num = num.replace(",", "")
    if not unit or unit.lower().strip() in _NOT_UNITS:
        return num
    return f"{num} {unit.lower().strip()}"


def _extract_from_line(line: str) -> Optional[Tuple[str, str]]:
    """Extract (topic, value) from one line, or None."""
    match = _EVERY_RE.match(line)
    if match:
        return (
            _normalize_topic(match.group("label")),
            _normalize_value(match.group("num"), match.group("unit")),
        )

    match = _WITHIN_RE.match(line)
    if match:
        return (
            _normalize_topic(match.group("label")),
            _normalize_value(match.group("num"), match.group("unit")),
        )

    match = _LABELED_FACT_RE.match(line)
    if match:
        number = _NUMBER_UNIT_RE.search(match.group("value"))
        if number:
            return (
                _normalize_topic(match.group("label")),
                _normalize_value(number.group("num"), number.group("unit")),
            )
    return None


def extract_claims(result: Dict[str, Any]) -> List[Claim]:
    """
    Extract all policy-fact claims from one search result.

    Args:
        result: A search result dict {'text', 'score', 'metadata', ...}
                as produced by either retriever.

    Returns:
        List of Claim objects (one per distinct extracted fact).
    """
    metadata = result.get("metadata", {})
    claims = []
    seen = set()

    for line in result.get("text", "").splitlines():
        extracted = _extract_from_line(line)
        if not extracted:
            continue
        topic, value = extracted
        key = (topic, value)
        if key in seen:
            continue
        seen.add(key)
        claims.append(Claim(
            topic=topic,
            value=value,
            line=line.strip(),
            doc_id=metadata.get("doc_id", "unknown"),
            version=metadata.get("version", "unknown"),
            effective_from=metadata.get("effective_from"),
            effective_to=metadata.get("effective_to"),
            is_current=bool(metadata.get("is_current", False)),
            score=float(result.get("score", 0.0)),
            chunk_id=metadata.get("chunk_id", ""),
        ))

    return claims


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def detect_conflicts(search_results: List[Dict[str, Any]]) -> List[Conflict]:
    """
    Detect conflicts among search results: the same policy topic carrying
    different values from different sources.

    Args:
        search_results: Search results from either retriever.

    Returns:
        List of Conflict objects (unordered).

    A conflict requires two DIFFERENT sources (doc_id, version) asserting
    different values for the same topic. Repeated agreement (many chunks,
    same value) is not a conflict.
    """
    by_topic: Dict[str, List[Claim]] = {}
    for result in search_results:
        for claim in extract_claims(result):
            by_topic.setdefault(claim.topic, []).append(claim)

    conflicts = []
    for topic, claims in by_topic.items():
        sources_per_value: Dict[str, set] = {}
        for claim in claims:
            sources_per_value.setdefault(claim.value, set()).add(
                (claim.doc_id, claim.version)
            )
        if len(sources_per_value) < 2:
            continue  # unanimous value (or only one value present)

        # Disagreement inside a single source (doc_id + version) is
        # extraction noise, not a version conflict.
        if len({(c.doc_id, c.version) for c in claims}) == 1:
            continue

        doc_ids = {c.doc_id for c in claims}
        conflicts.append(Conflict(
            topic=topic,
            claims=claims,
            kind="cross_document" if len(doc_ids) > 1 else "intra_document",
        ))
        logger.info(
            f"Conflict detected on '{topic}': "
            f"{sorted((v, sorted(s)) for v, s in sources_per_value.items())}"
        )

    return conflicts
