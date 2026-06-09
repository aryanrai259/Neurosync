# Purpose:      Basic entity extractor for the ingestion pipeline.
#               Scans normalised event text for known entity names and
#               returns a list of EntityMention objects.
#
#               Phase 3: exact substring match against seed name lists.
#               Phase 5+: replace with DB-backed lookup + NLP/NER models.
#
#               Kept separate from the normalizer because entity extraction
#               is a distinct concern: normalizers handle format conversion;
#               this module handles semantic understanding.
#
# Called By:    ingestion/worker.py
# Calls:        ingestion/schemas.py (EntityMention)
#               ingestion/constants.py (KNOWN_SERVICE_NAMES, KNOWN_TEAM_NAMES)
#               models/enums.py (EntityType)
# Dependencies: python stdlib (re)
# Test File:    tests/unit/ingestion/test_entity_extractor.py

from backend.ingestion.constants import KNOWN_SERVICE_NAMES, KNOWN_TEAM_NAMES
from backend.ingestion.schemas import EntityMention
from backend.models.enums import EntityType


class BasicEntityExtractor:
    """
    Identifies known entities in event text by exact case-insensitive substring match.

    The extractor is initialised with lists of known entity names. The defaults
    come from ingestion/constants.py (seeded from the AcmeCloud dataset spec).
    Override them in tests or when dynamically loading from the entity_registry.

    Limitations (all intentional for Phase 3):
    - No NLP / NER — purely lexical matching.
    - Does not resolve aliases (e.g. "auth svc" won't match "auth-service").
    - Confidence is always 1.0 for exact matches; 0.0 for no match (not returned).
    These limitations will be addressed in Phase 5 when the extractor gains
    access to the entity_registry and an embedding-based similarity fallback.
    """

    def __init__(
        self,
        service_names: list[str] | None = None,
        team_names: list[str] | None = None,
    ) -> None:
        self.service_names: list[str] = service_names if service_names is not None else KNOWN_SERVICE_NAMES
        self.team_names: list[str] = team_names if team_names is not None else KNOWN_TEAM_NAMES

    def extract(self, text: str) -> list[EntityMention]:
        """
        Scan text for known entity names and return all matches.

        Matching is case-insensitive. Each entity is returned at most once
        even if it appears multiple times in the text. Order of mentions
        follows the order of the name lists in constants.py.

        Returns an empty list if no known entities are found.
        """
        text_lower = text.lower()
        mentions: list[EntityMention] = []

        for name in self.service_names:
            if name.lower() in text_lower:
                mentions.append(
                    EntityMention(
                        name=name,
                        entity_type=EntityType.SERVICE,
                        confidence=1.0,
                    )
                )

        for name in self.team_names:
            if name.lower() in text_lower:
                mentions.append(
                    EntityMention(
                        name=name,
                        entity_type=EntityType.TEAM,
                        confidence=1.0,
                    )
                )

        return mentions
