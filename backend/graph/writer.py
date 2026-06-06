# Purpose:      Graph writer — upserts nodes and edges derived from a MemoryObject
#               into Neo4j. This is the only module that writes to Neo4j.
#               All Cypher MERGE statements live here.
#               Neo4j is a projection of PostgreSQL — not the source of truth.
#               Rebuilding from memory_objects is always possible.
# Called By:    ingestion/worker.py (_process_one_event, Phase 4C step)
# Calls:        graph/client.py (get_driver)
#               memory/memory_object.py (MemoryObject, EntityRef, RelationshipRef)
#               models/enums.py (EntityType)
# Dependencies: neo4j (official async driver), python stdlib (logging)
# Test File:    tests/integration/graph/test_graph_writer.py

import logging

from neo4j import AsyncDriver

from backend.memory.memory_object import EntityRef, MemoryObject, RelationshipRef
from backend.models.enums import EntityType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping from EntityType enum to Neo4j node label.
# Every entity type must have a label here.
# ---------------------------------------------------------------------------
_ENTITY_TYPE_TO_LABEL: dict[EntityType, str] = {
    EntityType.PERSON: "Person",
    EntityType.TEAM: "Team",
    EntityType.SERVICE: "Service",
    EntityType.REPOSITORY: "Repository",
    EntityType.TICKET: "Ticket",
    EntityType.DECISION: "Document",   # Decisions are stored as Document nodes
    EntityType.DOCUMENT: "Document",
}


async def _upsert_event_node(session, memory_object: MemoryObject) -> None:
    """Create or update the Event node for this memory object."""
    await session.run(
        """
        MERGE (e:Event {event_id: $event_id})
        ON CREATE SET
            e.workspace_id  = $workspace_id,
            e.source        = $source,
            e.timestamp     = $timestamp,
            e.title         = $title,
            e.author_id     = $author_id
        ON MATCH SET
            e.timestamp     = $timestamp,
            e.title         = $title
        """,
        event_id=str(memory_object.event_id),
        workspace_id=str(memory_object.workspace_id),
        source=memory_object.source.value,
        timestamp=memory_object.timestamp.isoformat(),
        title=memory_object.title or "",
        author_id=memory_object.author_id,
    )


async def _upsert_entity_node(session, entity: EntityRef, workspace_id: str) -> None:
    """Create or update a typed entity node, using the correct label."""
    label = _ENTITY_TYPE_TO_LABEL.get(entity.entity_type, "Entity")
    await session.run(
        f"""
        MERGE (n:{label} {{workspace_id: $workspace_id, canonical_name: $name}})
        ON CREATE SET
            n.confidence        = $confidence,
            n.extraction_source = $extraction_source
        ON MATCH SET
            n.confidence        = CASE
                WHEN $confidence > n.confidence THEN $confidence
                ELSE n.confidence
            END
        """,
        workspace_id=workspace_id,
        name=entity.canonical_name,
        confidence=entity.confidence,
        extraction_source=entity.extraction_source,
    )


async def _upsert_relationship(
    session,
    rel: RelationshipRef,
    workspace_id: str,
    event_id: str,
) -> None:
    """
    Create or update a directed relationship between two entity nodes.
    Uses dynamic labels — Neo4j Cypher requires label-based MERGE.
    If the subject or object is the Event itself (canonical_name == event_id),
    it matches the Event node.
    """
    subj_label = _ENTITY_TYPE_TO_LABEL.get(rel.subject.entity_type, "Entity")
    obj_label = _ENTITY_TYPE_TO_LABEL.get(rel.object.entity_type, "Entity")

    if rel.subject.canonical_name == event_id:
        subj_match = "MATCH (a:Event {event_id: $event_id})"
    else:
        subj_match = f"MATCH (a:{subj_label} {{workspace_id: $workspace_id, canonical_name: $subj_name}})"

    if rel.object.canonical_name == event_id:
        obj_match = "MATCH (b:Event {event_id: $event_id})"
    else:
        obj_match = f"MATCH (b:{obj_label} {{workspace_id: $workspace_id, canonical_name: $obj_name}})"

    cypher = f"""
        {subj_match}
        {obj_match}
        MERGE (a)-[r:{rel.predicate}]->(b)
        ON CREATE SET
            r.confidence        = $confidence,
            r.extraction_source = $extraction_source,
            r.source_event_id   = $event_id
        ON MATCH SET
            r.confidence = CASE
                WHEN $confidence > r.confidence THEN $confidence
                ELSE r.confidence
            END
    """
    await session.run(
        cypher,
        workspace_id=workspace_id,
        event_id=event_id,
        subj_name=rel.subject.canonical_name,
        obj_name=rel.object.canonical_name,
        confidence=rel.confidence,
        extraction_source=rel.extraction_source,
    )


class GraphWriter:
    """
    Writes a MemoryObject's entities and relationships to Neo4j.

    For each MemoryObject:
      1. Upsert the Event node (anchor for all relationships).
      2. Upsert each entity node (Person, Team, Service, etc.).
      3. Upsert each relationship edge (AUTHORED, AFFECTS, etc.).

    All operations use MERGE — idempotent. Re-processing the same MemoryObject
    does not create duplicates. Confidence is updated to the higher value.
    """

    def __init__(self, driver: AsyncDriver) -> None:
        self.driver = driver

    async def write(self, memory_object: MemoryObject) -> None:
        """
        Write a MemoryObject to Neo4j as nodes and edges.

        Runs all writes in a single async Neo4j session.
        Raises on Neo4j connectivity or constraint errors.
        """
        workspace_id = str(memory_object.workspace_id)
        event_id = str(memory_object.event_id)

        async with self.driver.session() as session:
            # Step 1: Event node
            await _upsert_event_node(session, memory_object)

            # Step 2: Entity nodes
            for entity in memory_object.entities:
                try:
                    await _upsert_entity_node(session, entity, workspace_id)
                except Exception as exc:
                    logger.warning(
                        "graph write: entity node failed [%s/%s]: %s",
                        entity.entity_type.value, entity.canonical_name, exc,
                    )

            # Step 3: Relationship edges
            for rel in memory_object.relationships:
                try:
                    await _upsert_relationship(session, rel, workspace_id, event_id)
                except Exception as exc:
                    logger.warning(
                        "graph write: relationship failed [%s -[%s]-> %s]: %s",
                        rel.subject.canonical_name, rel.predicate,
                        rel.object.canonical_name, exc,
                    )

        logger.debug(
            "graph write: event=%s entities=%d relationships=%d",
            event_id, len(memory_object.entities), len(memory_object.relationships),
        )
