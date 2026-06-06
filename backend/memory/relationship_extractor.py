# Purpose:      Relationship extractor — converts (NormalizedEvent, list[EntityRef])
#               into a list of RelationshipRefs using deterministic named rules.
#               Supports exactly 7 canonical predicates:
#                 AUTHORED, OWNS, DEPENDS_ON, REFERENCES, DISCUSSED_IN, AFFECTS, RELATED_TO
#               No LLM. Every rule is an isolated named function.
#               Each relationship carries confidence + extraction_source for provenance.
# Called By:    memory/memory_constructor.py
# Calls:        memory/memory_object.py (EntityRef, RelationshipRef)
#               models/enums.py (EntityType, SourceType)
# Dependencies: python stdlib (logging)
# Test File:    tests/unit/memory/test_relationship_extractor.py

import logging

from backend.memory.memory_object import EntityRef, RelationshipRef
from backend.models.enums import EntityType, SourceType
from backend.models.event import NormalizedEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule: AUTHORED
# Person → authored → Event represented by its source_id.
# Applied whenever a PERSON entity is found in the event.
# ---------------------------------------------------------------------------

def _rule_authored(
    event: NormalizedEvent,
    entities: list[EntityRef],
) -> list[RelationshipRef]:
    """
    Rule: AUTHORED — Person → Event.
    A Person entity is inferred to be the author of this event.
    Applies to all sources. Confidence follows the entity's confidence.
    """
    rels: list[RelationshipRef] = []
    persons = [e for e in entities if e.entity_type == EntityType.PERSON]
    event_ref = EntityRef(
        canonical_name=str(event.id),
        entity_type=EntityType.DOCUMENT,  # Events are treated as document nodes
        confidence=1.0,
        extraction_source="event_identity",
    )
    for person in persons:
        # Only the primary author gets AUTHORED; others in mentions get DISCUSSED_IN
        if person.extraction_source == "structured_author_id":
            rels.append(RelationshipRef(
                subject=person,
                predicate="AUTHORED",
                object=event_ref,
                confidence=person.confidence,
                extraction_source="rule_authored_structured",
            ))
    return rels


# ---------------------------------------------------------------------------
# Rule: AFFECTS
# Event → affects → Service.
# Applied when a SERVICE entity appears in the event content.
# ---------------------------------------------------------------------------

def _rule_affects(
    event: NormalizedEvent,
    entities: list[EntityRef],
) -> list[RelationshipRef]:
    """
    Rule: AFFECTS — Event → Service.
    If a service entity is mentioned in this event, the event affects it.
    Confidence is inherited from the entity extraction tier.
    """
    rels: list[RelationshipRef] = []
    services = [e for e in entities if e.entity_type == EntityType.SERVICE]
    event_ref = EntityRef(
        canonical_name=str(event.id),
        entity_type=EntityType.DOCUMENT,
        confidence=1.0,
        extraction_source="event_identity",
    )
    for service in services:
        rels.append(RelationshipRef(
            subject=event_ref,
            predicate="AFFECTS",
            object=service,
            confidence=service.confidence,
            extraction_source="rule_affects_service_mention",
        ))
    return rels


# ---------------------------------------------------------------------------
# Rule: DISCUSSED_IN
# Service → discussed_in → Event.
# Complementary to AFFECTS — from the service's point of view.
# ---------------------------------------------------------------------------

def _rule_discussed_in(
    event: NormalizedEvent,
    entities: list[EntityRef],
) -> list[RelationshipRef]:
    """
    Rule: DISCUSSED_IN — Service → Event.
    Every service mentioned in an event was discussed in it.
    """
    rels: list[RelationshipRef] = []
    services = [e for e in entities if e.entity_type == EntityType.SERVICE]
    event_ref = EntityRef(
        canonical_name=str(event.id),
        entity_type=EntityType.DOCUMENT,
        confidence=1.0,
        extraction_source="event_identity",
    )
    for service in services:
        rels.append(RelationshipRef(
            subject=service,
            predicate="DISCUSSED_IN",
            object=event_ref,
            confidence=service.confidence,
            extraction_source="rule_discussed_in_service_mention",
        ))
    return rels


# ---------------------------------------------------------------------------
# Rule: REFERENCES
# Event → references → Ticket.
# Applied when a TICKET entity is found in event content.
# ---------------------------------------------------------------------------

def _rule_references(
    event: NormalizedEvent,
    entities: list[EntityRef],
) -> list[RelationshipRef]:
    """
    Rule: REFERENCES — Event → Ticket.
    When an event body contains a Jira/linear-style ticket ID,
    the event references that ticket.
    """
    rels: list[RelationshipRef] = []
    tickets = [e for e in entities if e.entity_type == EntityType.TICKET]
    event_ref = EntityRef(
        canonical_name=str(event.id),
        entity_type=EntityType.DOCUMENT,
        confidence=1.0,
        extraction_source="event_identity",
    )
    for ticket in tickets:
        rels.append(RelationshipRef(
            subject=event_ref,
            predicate="REFERENCES",
            object=ticket,
            confidence=ticket.confidence,
            extraction_source="rule_references_ticket",
        ))
    return rels


# ---------------------------------------------------------------------------
# Rule: OWNS
# Team → owns → Service.
# Applied when both a TEAM and a SERVICE appear in the same event.
# Confidence is 0.6 (co-occurrence inference — weakest rule).
# Phase 5+ should replace this with a workspace ownership map.
# ---------------------------------------------------------------------------

def _rule_owns(entities: list[EntityRef]) -> list[RelationshipRef]:
    """
    Rule: OWNS — Team → Service.
    INTENTIONALLY DISABLED to prevent graph super-node growth. Ownership inference
    requires authoritative ownership sources and is deferred to Phase 5.
    """
    return []


# ---------------------------------------------------------------------------
# Rule: RELATED_TO
# Entity → related_to → Entity (generic fallback for co-occurring pairs).
# Applied when two non-Person entities of different types co-occur.
# Confidence is 0.6.
# ---------------------------------------------------------------------------

def _rule_related_to(entities: list[EntityRef]) -> list[RelationshipRef]:
    """
    Rule: RELATED_TO — generic co-occurrence relationship.
    INTENTIONALLY DISABLED to prevent graph super-node growth. The resulting dense
    edges degrade graph retrieval precision.
    """
    return []


# ---------------------------------------------------------------------------
# Rule: DEPENDS_ON
# Service → depends_on → Service.
# Phase 4 MVP: GitHub PRs that mention two or more services together.
# ---------------------------------------------------------------------------

def _rule_depends_on(
    event: NormalizedEvent,
    entities: list[EntityRef],
) -> list[RelationshipRef]:
    """
    Rule: DEPENDS_ON — Service → Service.
    Applied only for GitHub events when two or more service entities appear.
    The first service in list order is assumed to depend on the second.
    Confidence is 0.7.
    Phase 5+: replace with explicit dependency declarations from workspace config.
    """
    if event.source != SourceType.GITHUB:
        return []

    rels: list[RelationshipRef] = []
    services = [e for e in entities if e.entity_type == EntityType.SERVICE]

    # Only infer when exactly 2 services to avoid combinatorial noise
    if len(services) == 2:
        rels.append(RelationshipRef(
            subject=services[0],
            predicate="DEPENDS_ON",
            object=services[1],
            confidence=0.7,
            extraction_source="rule_depends_on_github_cooccurrence",
        ))
    return rels


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class RelationshipExtractor:
    """
    Extracts RelationshipRefs from a NormalizedEvent and its resolved entities.

    Applies all seven deterministic rules in sequence. Each rule is a standalone
    named function — easy to test, easy to disable, easy to explain.

    Rules applied:
      1. AUTHORED     — structured author field → Person AUTHORED Event
      2. AFFECTS      — Service entity → Event AFFECTS Service
      3. DISCUSSED_IN — Service entity → Service DISCUSSED_IN Event
      4. REFERENCES   — Ticket entity → Event REFERENCES Ticket
      5. OWNS         — Team + Service co-occurrence → Team OWNS Service (weak)
      6. DEPENDS_ON   — GitHub + 2 Services → Service DEPENDS_ON Service (weak)
      7. RELATED_TO   — generic non-Person co-occurrence fallback (weakest)

    Returns empty list if no relationships apply — never None.
    """

    def extract(
        self,
        event: NormalizedEvent,
        entities: list[EntityRef],
    ) -> list[RelationshipRef]:
        """
        Run all relationship rules and return the combined result.
        No deduplication — each rule produces distinct relationship types.
        """
        if not entities:
            return []

        rels: list[RelationshipRef] = []
        rels.extend(_rule_authored(event, entities))
        rels.extend(_rule_affects(event, entities))
        rels.extend(_rule_discussed_in(event, entities))
        rels.extend(_rule_references(event, entities))
        rels.extend(_rule_owns(entities))
        rels.extend(_rule_depends_on(event, entities))
        rels.extend(_rule_related_to(entities))
        return rels
