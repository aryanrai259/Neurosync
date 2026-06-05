# Purpose:      Ingestion worker — orchestrates the full pipeline for one job.
#               Receives a job_id and a list of RawEvents, then:
#                 1. Marks the job PROCESSING
#                 2. Fetches events from the adapter
#                 3. Normalizes each event
#                 4. Deduplicates against the events table
#                 5. Persists new events via event_repo
#                 6. Extracts entities and registers them
#                 7. Marks the job COMPLETED or FAILED
#
#               Business logic lives here — NOT in the API layer.
#               The worker is a plain async class. It can be called from:
#                 - FastAPI BackgroundTasks (Phase 3A)
#                 - Celery tasks (Phase 6+)
#                 - Direct test calls (all test phases)
#               Swapping the runner does not require changing this class.
#
# Called By:    api/v1/ingest.py (via FastAPI BackgroundTasks)
# Calls:        ingestion/adapters/synthetic.py (SyntheticAdapter)
#               ingestion/normalizers/slack.py  (SlackNormalizer)
#               ingestion/normalizers/github.py (GithubNormalizer)
#               ingestion/normalizers/jira.py   (JiraNormalizer)
#               ingestion/deduplicator.py       (Deduplicator)
#               ingestion/entity_extractor.py   (BasicEntityExtractor)
#               db/repositories/event_repo.py
#               db/repositories/ingestion_repo.py
#               db/repositories/entity_registry_repo.py
# Dependencies: sqlalchemy (AsyncSession), python stdlib (logging, time, uuid)
# Test File:    tests/integration/ingestion/test_worker.py

import logging
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.entity_registry_repo import EntityRegistryRepository
from backend.db.repositories.event_repo import EventRepository
from backend.db.repositories.ingestion_repo import IngestionRepository
from backend.db.session import async_session
from backend.ingestion.adapters.base import BaseAdapter
from backend.ingestion.deduplicator import Deduplicator
from backend.ingestion.entity_extractor import BasicEntityExtractor
from backend.ingestion.normalizers.github import GithubNormalizer
from backend.ingestion.normalizers.jira import JiraNormalizer
from backend.ingestion.normalizers.slack import SlackNormalizer
from backend.ingestion.schemas import RawEvent
from backend.models.enums import IngestionStatus, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalizer registry — maps SourceType to the class that handles it.
# Add new source normalizers here as Phase 3B+ adds more sources.
# ---------------------------------------------------------------------------
_NORMALIZER_MAP = {
    SourceType.SLACK: SlackNormalizer(),
    SourceType.GITHUB: GithubNormalizer(),
    SourceType.JIRA: JiraNormalizer(),
}


class IngestionWorker:
    """
    Orchestrates one complete ingestion job end-to-end.

    Dependencies are injected to keep the worker fully testable without HTTP.
    All DB repositories are passed in; the worker never imports repo singletons.
    The session_factory defaults to the global async_session from db/session.py
    but can be overridden in tests to point at a test database.
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        deduplicator: Deduplicator,
        extractor: BasicEntityExtractor,
        event_repo: EventRepository,
        ingestion_repo: IngestionRepository,
        entity_registry_repo: EntityRegistryRepository,
        session_factory=None,
    ) -> None:
        self.adapter = adapter
        self.deduplicator = deduplicator
        self.extractor = extractor
        self.event_repo = event_repo
        self.ingestion_repo = ingestion_repo
        self.entity_registry_repo = entity_registry_repo
        # Use the global session factory by default; override in tests
        self.session_factory = session_factory or async_session

    async def run_job(self, job_id: UUID) -> None:
        """
        Execute one ingestion job.

        Opens its own DB session so it can run as a BackgroundTask after the
        HTTP response has been sent (the request session is already closed).

        Marks the job PROCESSING at start. On any unhandled exception, marks
        FAILED. On normal completion, marks COMPLETED with event counts.
        """
        async with self.session_factory() as session:
            await self._execute(job_id, session)

    async def _execute(
        self, job_id: UUID, session: AsyncSession
    ) -> None:
        """
        Inner execution — separated so integration tests can inject a session.
        """
        started = time.monotonic()

        # Transition job to PROCESSING
        claimed = await self.ingestion_repo.mark_processing(session, job_id)
        if not claimed:
            logger.warning("job %s could not be claimed (already PROCESSING or not found)", job_id)
            return

        # Retrieve the job record to read workspace_id
        job = await self.ingestion_repo.get_by_id(session, job_id)
        if job is None:
            logger.error("job %s not found after mark_processing", job_id)
            return

        workspace_id: UUID = job.workspace_id

        events_ingested = 0
        events_failed = 0
        events_skipped = 0

        try:
            # Step 1: fetch events from adapter
            fetched = await self.adapter.fetch_events()
            logger.info("job %s: adapter returned %d events", job_id, len(fetched))

            for raw in fetched:
                try:
                    await self._process_one_event(session, workspace_id, raw)
                    events_ingested += 1
                except _DuplicateEvent:
                    events_skipped += 1
                    logger.debug(
                        "job %s: skipped duplicate %s/%s", job_id, raw.source, raw.source_id
                    )
                except Exception as exc:  # noqa: BLE001
                    events_failed += 1
                    logger.warning(
                        "job %s: failed to process event %s/%s: %s",
                        job_id, raw.source, raw.source_id, exc,
                    )

        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.error("job %s: unhandled error — marking FAILED: %s", job_id, exc)
            await self.ingestion_repo.mark_failed(session, job_id, str(exc))
            return

        elapsed_ms = int((time.monotonic() - started) * 1000)
        await self.ingestion_repo.mark_completed(
            session=session,
            job_id=job_id,
            events_ingested=events_ingested,
            events_failed=events_failed,
            processing_time_ms=elapsed_ms,
        )
        logger.info(
            "job %s: COMPLETED — ingested=%d skipped=%d failed=%d in %dms",
            job_id, events_ingested, events_skipped, events_failed, elapsed_ms,
        )

    async def _process_one_event(
        self, session: AsyncSession, workspace_id: UUID, raw: RawEvent
    ) -> None:
        """
        Process a single RawEvent:
          1. Look up the normalizer for this source type.
          2. Normalize the raw event.
          3. Check for duplicate.
          4. Write to events table.
          5. Extract entities and register them.

        Raises _DuplicateEvent if the event already exists.
        Raises Exception if normalization or persistence fails.
        """
        normalizer = _NORMALIZER_MAP.get(raw.source)
        if normalizer is None:
            raise ValueError(f"No normalizer registered for source: {raw.source}")

        # Normalize
        normalized = normalizer.normalize(raw, workspace_id)

        # Deduplicate
        is_dup = await self.deduplicator.is_duplicate(
            session=session,
            workspace_id=workspace_id,
            source=normalized.source,
            source_id=normalized.source_id,
        )
        if is_dup:
            raise _DuplicateEvent()

        # Persist event
        await self.event_repo.upsert_event(
            session=session,
            workspace_id=workspace_id,
            source=normalized.source,
            source_id=normalized.source_id,
            content=normalized.content,
            author_id=normalized.author_id,
            timestamp=normalized.timestamp,
            title=normalized.title,
            author_name=normalized.author_name,
            url=normalized.url,
            metadata_json=normalized.metadata,
        )

        # Extract and register entities
        mentions = self.extractor.extract(normalized.content)
        for mention in mentions:
            await self.entity_registry_repo.register_entity(
                session=session,
                workspace_id=workspace_id,
                entity_type=mention.entity_type,
                canonical_name=mention.name,
            )


class _DuplicateEvent(Exception):
    """
    Internal sentinel raised when an event is a known duplicate.
    Used to distinguish "skip" from "error" without polluting the events_failed count.
    Private to this module — never raised outside the worker.
    """
