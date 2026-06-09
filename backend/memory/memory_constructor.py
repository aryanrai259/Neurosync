# Purpose:      Memory constructor — orchestrates Phase 4A for one event.
#               Takes a NormalizedEvent and a persisted event_id, then:
#                 1. Resolves entities deterministically via EntityResolver
#                 2. Extracts relationships via RelationshipExtractor
#                 3. Builds the MemoryObject
#                 4. Persists extraction result to memory_objects table
#               Returns the MemoryObject for downstream use (Phase 4B, 4C).
#               If persistence fails, logs and re-raises so the worker can
#               handle it gracefully.
# Called By:    ingestion/worker.py (_process_one_event)
# Calls:        memory/entity_resolver.py (EntityResolver)
#               memory/relationship_extractor.py (RelationshipExtractor)
#               memory/memory_object.py (MemoryObject)
#               db/repositories/memory_repo.py (MemoryObjectRepository)
# Dependencies: sqlalchemy (AsyncSession), python stdlib (logging, uuid)
# Test File:    tests/integration/memory/test_memory_constructor.py

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.memory_repo import MemoryObjectRepository
from backend.memory.entity_resolver import EntityResolver
from backend.memory.memory_object import MemoryObject
from backend.memory.relationship_extractor import RelationshipExtractor
from backend.models.event import NormalizedEvent

logger = logging.getLogger(__name__)


class MemoryConstructor:
    """
    Orchestrates Phase 4A memory construction for a single event.

    Dependency injection keeps this class testable without a real database:
    pass in mock resolver, extractor, and repo in unit tests; use the
    real implementations and a real session in integration tests.

    Usage:
        constructor = MemoryConstructor(resolver, extractor, repo)
        memory_object = await constructor.construct(event, event_id, session)
    """

    def __init__(
        self,
        resolver: EntityResolver,
        extractor: RelationshipExtractor,
        repo: MemoryObjectRepository,
    ) -> None:
        self.resolver = resolver
        self.extractor = extractor
        self.repo = repo

    async def construct(
        self,
        event: NormalizedEvent,
        event_id: UUID,
        session: AsyncSession,
    ) -> MemoryObject:
        """
        Build and persist a MemoryObject for one NormalizedEvent.

        Args:
            event:    The fully normalized event (output of Phase 3 normalizer).
            event_id: The UUID of the persisted EventModel row. Used as provenance.
            session:  Active DB session — caller owns the transaction boundary.

        Returns:
            MemoryObject ready for Phase 4B (vector) and 4C (graph) processing.

        Raises:
            Exception if memory_objects persistence fails — logged and re-raised
            so the ingestion worker can mark the event as failed gracefully.
        """
        # Step 1: entity resolution
        entities = self.resolver.resolve(event)
        logger.debug(
            "memory construct: event %s resolved %d entities",
            event_id, len(entities),
        )

        # Step 2: relationship extraction
        relationships = self.extractor.extract(event, entities)
        logger.debug(
            "memory construct: event %s extracted %d relationships",
            event_id, len(relationships),
        )

        # Step 3: build MemoryObject
        memory_object = MemoryObject(
            event_id=event_id,
            workspace_id=event.workspace_id,
            source=event.source,
            content=event.content,
            title=event.title,
            author_id=event.author_id,
            timestamp=event.timestamp,
            entities=entities,
            relationships=relationships,
            metadata=event.metadata,
        )

        # Step 4: persist extraction result
        try:
            await self.repo.insert(session, memory_object)
        except Exception as exc:
            logger.error(
                "memory construct: failed to persist memory_object for event %s: %s",
                event_id, exc,
            )
            raise

        return memory_object
