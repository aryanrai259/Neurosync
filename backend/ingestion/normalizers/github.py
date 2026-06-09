# Purpose:      GitHub event normalizer.
#               Converts a RawEvent from a GitHub source into a NormalizedEvent.
#               Handles PRs and issues. PR number and repo name go into title.
#               Reviewers, labels, and branch names go into metadata.
# Called By:    ingestion/worker.py (via NORMALIZER_MAP[SourceType.GITHUB])
# Calls:        ingestion/normalizers/_parsing.py
#               models/event.py (NormalizedEvent)
#               ingestion/schemas.py (RawEvent)
#               ingestion/constants.py (SOURCE_AUTHORITY_MAP)
# Dependencies: python stdlib (uuid)
# Test File:    tests/unit/ingestion/test_normalizers.py

from uuid import UUID

from backend.ingestion.constants import SOURCE_AUTHORITY_MAP
from backend.ingestion.normalizers._parsing import parse_iso_timestamp
from backend.ingestion.schemas import RawEvent
from backend.models.enums import SourceType
from backend.models.event import NormalizedEvent


class GithubNormalizer:
    """
    Normalizes a raw GitHub event (PR or issue) into a NormalizedEvent.

    Authority score for GitHub PRs is 0.75 — higher than Slack but lower than
    Jira tickets. PRs contain implementation decisions and are code-reviewed,
    making them reliable but not as authoritative as formal ADRs.

    Title is built from the PR/issue number and repo name when available.
    """

    def normalize(self, raw: RawEvent, workspace_id: UUID) -> NormalizedEvent:
        """
        Convert a GitHub RawEvent to a NormalizedEvent.

        Field mapping:
          raw.source_id     → source_id (commit SHA, PR number, or issue number)
          raw.raw_content   → content   (PR description, issue body, or commit message)
          raw.raw_author    → author_id (GitHub username)
          raw.raw_timestamp → timestamp (parsed ISO 8601)
          raw.extra         → metadata  (pr_number, repo, labels, reviewers, authority_score)

        Title format: "[repo] PR #42: <title>" or "[repo] Issue #7: <title>"
        Falls back to None if no title or repo is provided.
        """
        timestamp = parse_iso_timestamp(raw.raw_timestamp)

        repo = raw.extra.get("repo", "")
        event_title = raw.extra.get("title")
        pr_number = raw.extra.get("pr_number")
        issue_number = raw.extra.get("issue_number")

        if event_title and repo and pr_number:
            title = f"[{repo}] PR #{pr_number}: {event_title}"
        elif event_title and repo and issue_number:
            title = f"[{repo}] Issue #{issue_number}: {event_title}"
        elif event_title:
            title = event_title
        else:
            title = None

        metadata = {
            **raw.extra,
            "authority_score": SOURCE_AUTHORITY_MAP["github"],
        }

        return NormalizedEvent(
            source=SourceType.GITHUB,
            workspace_id=workspace_id,
            source_id=raw.source_id,
            content=raw.raw_content,
            title=title,
            author_id=raw.raw_author,
            author_name=raw.extra.get("author_name"),
            url=raw.extra.get("url"),
            timestamp=timestamp,
            metadata=metadata,
        )
