# backend/ingestion

## Purpose
Converts raw source payloads into canonical `NormalizedEvent` objects and
persists them to PostgreSQL. The full pipeline runs as a background task
after the HTTP endpoint returns `202 Accepted`.

## Phase 3A Status: ✅ Implemented

## Package Structure

```
backend/ingestion/
├── __init__.py            # Package marker
├── constants.py           # SOURCE_AUTHORITY_MAP, KNOWN_SERVICE_NAMES, KNOWN_TEAM_NAMES
├── schemas.py             # RawEvent, EntityMention, SyntheticJobRequest, JobSubmittedResponse
├── deduplicator.py        # Deduplicator — checks events table for duplicate source_id
├── entity_extractor.py    # BasicEntityExtractor — finds known entities in event text
├── worker.py              # IngestionWorker — orchestrates the full pipeline
├── adapters/
│   ├── __init__.py
│   └── synthetic.py       # SyntheticAdapter — pass-through for pre-formed RawEvents
└── normalizers/
    ├── __init__.py
    ├── _parsing.py        # Shared: parse_iso_timestamp, strip_slack_mentions
    ├── slack.py           # SlackNormalizer
    ├── github.py          # GithubNormalizer
    └── jira.py            # JiraNormalizer
```

## Exact Data Flow

```
POST /api/v1/ingest/synthetic
  │
  ▼
ingest.py: validate workspace → create ingestion_job (PENDING) → return 202
  │  (BackgroundTask fires after response)
  ▼
IngestionWorker.run_job(job_id, raw_events)
  │  marks job PROCESSING
  ▼
SyntheticAdapter.fetch_events(raw_events)    ← pass-through
  │
  for each RawEvent:
  ▼
  SlackNormalizer.normalize(raw, workspace_id)  ← or Github/Jira
  │  returns NormalizedEvent
  ▼
  Deduplicator.is_duplicate(session, ...)
  │  queries events table; if True → skip
  ▼
  event_repo.upsert_event(session, ...)
  │  writes to events table
  ▼
  BasicEntityExtractor.extract(content)
  │  returns list[EntityMention]
  ▼
  entity_registry_repo.register_entity(...)   ← for each mention
  │  upserts into entity_registry
  │
  ▼
worker marks job COMPLETED (or FAILED)
```

## Authority Scores (constants.py)

| Source   | Score |
|----------|-------|
| adr      | 1.00  |
| incident | 0.90  |
| jira     | 0.80  |
| github   | 0.75  |
| slack    | 0.60  |

## Adding a New Source (Phase 3B+)

1. Add `SourceType.FOO` to `models/enums.py`
2. Create `ingestion/normalizers/foo.py` with a `FooNormalizer` class
3. Register in `ingestion/worker.py` `_NORMALIZER_MAP`
4. Add source authority score to `ingestion/constants.py`
5. Create `ingestion/adapters/foo.py` with a `FooAdapter` class
6. Add API endpoint in `api/v1/ingest.py`

## Dependencies
- `models/event.py` (NormalizedEvent)
- `models/enums.py` (SourceType, EntityType)
- `db/repositories/event_repo.py`
- `db/repositories/ingestion_repo.py`
- `db/repositories/entity_registry_repo.py`
