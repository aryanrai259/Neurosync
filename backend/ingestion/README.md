# backend/ingestion

## Purpose
Converts raw source payloads (Slack, GitHub, Jira, Notion, email) into
canonical `NormalizedEvent` objects. This is the entry point for all data
entering Company Brain.

## Responsibilities
- Connect to external source APIs
- Fetch raw events/messages/commits/tickets
- Normalize them into the canonical `NormalizedEvent` schema
- Pass normalized events downstream to storage and graph layers

## Files (to be added)
| File | Source | Responsibility |
|---|---|---|
| `slack.py` | Slack API | Ingest messages, threads, reactions |
| `github.py` | GitHub API | Ingest commits, PRs, issues, comments |
| `jira.py` | Jira API | Ingest tickets, status changes, comments |
| `notion.py` | Notion API | Ingest pages, databases, comments |
| `email.py` | IMAP/Gmail | Ingest email threads |
| `normalizer.py` | — | Shared normalization logic |
| `scheduler.py` | — | Cron-based ingestion scheduler |

## Dependency Arrow
```
External APIs (Slack, GitHub, Jira, Notion, Email)
  ↓
ingestion/ (this module)
  ↓
models/event.py  (NormalizedEvent)
  ↓
storage/postgres.py + graph/transformer.py
```

## Inputs
- Raw API payloads (JSON) from each source

## Outputs
- `NormalizedEvent` (defined in `models/event.py`)

## Dependencies
- `models/event.py`
- `models/entity.py`
- `core/config.py` (API keys, rate limits)
- `core/logging.py`

## Future Extensions
- Webhook listeners (instead of polling)
- Real-time Slack socket mode
- Confluence adapter
- Linear adapter

## Example Flow
```
Slack API → raw message JSON
  → ingestion/slack.py
  → ingestion/normalizer.py
  → NormalizedEvent(source="slack", workspace_id=..., ...)
  → storage/postgres.py (persisted)
  → graph/transformer.py (entities extracted)
```
