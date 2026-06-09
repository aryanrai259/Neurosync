# Purpose:      Entity resolver — converts a NormalizedEvent into a list of EntityRefs.
#               Uses a strict three-tier deterministic strategy:
#                 Tier 1: Structured fields (confidence=1.0)
#                 Tier 2: Seed list exact matching (confidence=1.0)
#                 Tier 3: Regex pattern matching (confidence=0.85)
#               No LLM. No fuzzy matching. Every rule is a named function.
#               Produces canonical, deduplicated EntityRefs.
# Called By:    memory/memory_constructor.py
# Calls:        memory/memory_object.py (EntityRef)
#               ingestion/constants.py (KNOWN_SERVICE_NAMES, KNOWN_TEAM_NAMES)
#               models/enums.py (EntityType, SourceType)
# Dependencies: python stdlib (re, logging)
# Test File:    tests/unit/memory/test_entity_resolver.py

import logging
import re

from backend.ingestion.constants import KNOWN_SERVICE_NAMES, KNOWN_TEAM_NAMES
from backend.memory.memory_object import EntityRef
from backend.models.enums import EntityType, SourceType
from backend.models.event import NormalizedEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled regex patterns — compiled once at module load, never at call time.
# ---------------------------------------------------------------------------
_PATTERN_TICKET = re.compile(r"\b([A-Z]{2,10}-\d{1,6})\b")
_PATTERN_MENTION = re.compile(r"@(\w{2,50})")
_PATTERN_REPO = re.compile(r"\b([a-zA-Z0-9_-]{2,50}/[a-zA-Z0-9_-]{2,100})\b")

# Known technology names mapped to SERVICE entity type.
# These supplement the KNOWN_SERVICE_NAMES seed list with common infra terms.
_KNOWN_TECH_NAMES: list[str] = [
    "redis",
    "postgres",
    "postgresql",
    "kafka",
    "elasticsearch",
    "rabbitmq",
    "mongodb",
    "mysql",
    "nginx",
    "kubernetes",
    "docker",
]


# ---------------------------------------------------------------------------
# Tier 1: Structured field extraction
# ---------------------------------------------------------------------------

def _extract_from_structured_fields(event: NormalizedEvent) -> list[EntityRef]:
    """
    Extract entities from well-structured, typed fields of a NormalizedEvent.
    Confidence is 1.0 — these come from source system metadata, not free text.
    """
    refs: list[EntityRef] = []

    # Author is always a PERSON when not 'unknown' or empty
    author = event.author_id.strip()
    if author and author.lower() not in ("unknown", "bot", "system"):
        refs.append(EntityRef(
            canonical_name=author.lower(),
            entity_type=EntityType.PERSON,
            confidence=1.0,
            extraction_source="structured_author_id",
        ))

    # GitHub: repository from metadata
    if event.source == SourceType.GITHUB:
        repo = event.metadata.get("repo", "").strip()
        if repo and "/" in repo:
            refs.append(EntityRef(
                canonical_name=repo.lower(),
                entity_type=EntityType.REPOSITORY,
                confidence=1.0,
                extraction_source="structured_github_repo",
            ))

        # GitHub labels → potential TICKET or DECISION markers
        labels: list[str] = event.metadata.get("labels", [])
        for label in labels:
            if label.lower() in ("decision", "adr", "architecture"):
                # The event itself is about a decision, not that the label is an entity.
                # We mark the event's source_id as a decision entity.
                refs.append(EntityRef(
                    canonical_name=f"decision:{event.source_id}",
                    entity_type=EntityType.DECISION,
                    confidence=1.0,
                    extraction_source="structured_github_label",
                ))
                break

    return refs


# ---------------------------------------------------------------------------
# Tier 2: Seed list exact matching
# ---------------------------------------------------------------------------

def _extract_from_seed_lists(
    content: str,
    service_names: list[str],
    team_names: list[str],
) -> list[EntityRef]:
    """
    Scan lowercased content for exact case-insensitive matches against
    known service and team name seed lists. Confidence is 1.0.
    """
    content_lower = content.lower()
    refs: list[EntityRef] = []

    for name in service_names:
        if name.lower() in content_lower:
            refs.append(EntityRef(
                canonical_name=name.lower(),
                entity_type=EntityType.SERVICE,
                confidence=1.0,
                extraction_source="seed_list_service",
            ))

    for name in team_names:
        if name.lower() in content_lower:
            refs.append(EntityRef(
                canonical_name=name.lower(),
                entity_type=EntityType.TEAM,
                confidence=1.0,
                extraction_source="seed_list_team",
            ))

    for name in _KNOWN_TECH_NAMES:
        if name in content_lower:
            refs.append(EntityRef(
                canonical_name=name,
                entity_type=EntityType.SERVICE,
                confidence=1.0,
                extraction_source="seed_list_tech",
            ))

    return refs


# ---------------------------------------------------------------------------
# Tier 3: Regex / pattern matching
# ---------------------------------------------------------------------------

def _extract_from_patterns(content: str, source: SourceType) -> list[EntityRef]:
    """
    Use compiled regex patterns to extract entity mentions.
    Confidence is 0.85 — pattern extraction is reliable but not infallible.
    """
    refs: list[EntityRef] = []

    # Jira/linear-style tickets: PROJ-1234, AUTH-99, etc.
    for match in _PATTERN_TICKET.finditer(content):
        refs.append(EntityRef(
            canonical_name=match.group(1).upper(),
            entity_type=EntityType.TICKET,
            confidence=0.85,
            extraction_source="pattern_ticket",
        ))

    # @mentions in Slack events
    if source == SourceType.SLACK:
        for match in _PATTERN_MENTION.finditer(content):
            name = match.group(1).lower()
            if name not in ("here", "channel", "everyone", "all"):
                refs.append(EntityRef(
                    canonical_name=name,
                    entity_type=EntityType.PERSON,
                    confidence=0.85,
                    extraction_source="pattern_mention",
                ))

    return refs


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _deduplicate(refs: list[EntityRef]) -> list[EntityRef]:
    """
    Remove duplicate EntityRefs by (canonical_name, entity_type).
    When duplicates exist, keep the one with the highest confidence.
    Warns (does not error) if two same-name entities have different types.
    """
    best: dict[tuple[str, EntityType], EntityRef] = {}
    for ref in refs:
        key = (ref.canonical_name, ref.entity_type)
        existing = best.get(key)
        if existing is None or ref.confidence > existing.confidence:
            best[key] = ref

    # Warn on alias collisions across different types (same name, different type)
    by_name: dict[str, list[EntityRef]] = {}
    for ref in best.values():
        by_name.setdefault(ref.canonical_name, []).append(ref)
    for name, group in by_name.items():
        if len(group) > 1:
            types = [r.entity_type.value for r in group]
            logger.warning(
                "EntityResolver: '%s' matched multiple entity types %s. "
                "Keeping all — resolve manually.",
                name, types,
            )

    return list(best.values())


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class EntityResolver:
    """
    Converts a NormalizedEvent into a deduplicated list of EntityRefs.

    The resolver applies three extraction tiers in order:
      1. Structured fields (highest confidence)
      2. Seed list matching
      3. Regex pattern matching

    Results are deduplicated: same (canonical_name, entity_type) pair keeps
    the highest-confidence match. Conflicting type assignments for the same
    name are logged as warnings and kept distinct.

    Inject custom service/team lists in tests or for workspace-specific seeds.
    """

    def __init__(
        self,
        service_names: list[str] | None = None,
        team_names: list[str] | None = None,
    ) -> None:
        self.service_names: list[str] = (
            service_names if service_names is not None else KNOWN_SERVICE_NAMES
        )
        self.team_names: list[str] = (
            team_names if team_names is not None else KNOWN_TEAM_NAMES
        )

    def resolve(self, event: NormalizedEvent) -> list[EntityRef]:
        """
        Extract and deduplicate all EntityRefs from a NormalizedEvent.
        Returns an empty list if no entities are found — never None.
        """
        combined: list[EntityRef] = []
        combined.extend(_extract_from_structured_fields(event))
        combined.extend(
            _extract_from_seed_lists(event.content, self.service_names, self.team_names)
        )
        combined.extend(_extract_from_patterns(event.content, event.source))
        return _deduplicate(combined)
