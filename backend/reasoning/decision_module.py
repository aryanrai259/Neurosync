# Purpose:      Decision intelligence module — extracts decisions from retrieved
#               evidence chunks, stores them, and provides decision-centric reasoning.
#               A decision is identified when evidence contains patterns like
#               "decided to", "we will", "approved", "rejected", "chosen to", etc.
# Called By:    reasoning/pipeline.py (optional post-processing)
#               api/v1/decisions.py
# Calls:        db/repositories/decision_repo.py
# Dependencies: re, uuid, sqlalchemy
# Test File:    tests/unit/reasoning/test_decision_module.py

import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.decision import DecisionModel
from backend.db.repositories.decision_repo import decision_repo
from backend.models.query import RetrievedChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Decision extraction heuristics
# ---------------------------------------------------------------------------

# Patterns that suggest a decision statement in text
_DECISION_PATTERNS = [
    r"\bwe decided\b",
    r"\bwe will\b",
    r"\bdecided to\b",
    r"\bagreed to\b",
    r"\bapproved\b",
    r"\bchosen to\b",
    r"\brejected\b",
    r"\bwe agreed\b",
    r"\bthe decision is\b",
    r"\bgoing with\b",
    r"\bshipping\b.*\bv\d",
    r"\bwill adopt\b",
    r"\bwill use\b",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _DECISION_PATTERNS]

_DECIDED_BY_PATTERN = re.compile(
    r"(?:decided by|approved by|chosen by|by)\s+([A-Za-z][A-Za-z\s\-]{1,40})",
    re.IGNORECASE,
)


def extract_decision_candidates(chunks: list[RetrievedChunk]) -> list[dict]:
    """
    Scan retrieved chunks for decision statements.

    Returns a list of dicts:
      {title, description, decided_by, source_event_id}

    Heuristic: any chunk that matches at least one decision pattern
    is treated as a candidate decision.
    """
    candidates = []
    seen_event_ids: set[UUID] = set()

    for chunk in chunks:
        if chunk.event_id in seen_event_ids:
            continue
        content = chunk.content

        if not any(pat.search(content) for pat in _COMPILED_PATTERNS):
            continue

        # Extract title: first sentence or first 100 chars
        sentences = re.split(r'(?<=[.!?])\s', content.strip())
        title = sentences[0][:200] if sentences else content[:200]

        # Try to extract decided_by
        decided_by = None
        match = _DECIDED_BY_PATTERN.search(content)
        if match:
            decided_by = match.group(1).strip()

        candidates.append({
            "title": title,
            "description": content[:1000],
            "decided_by": decided_by,
            "source_event_id": chunk.event_id,
        })
        seen_event_ids.add(chunk.event_id)

    return candidates


async def extract_and_persist_decisions(
    session: AsyncSession,
    workspace_id: UUID,
    chunks: list[RetrievedChunk],
) -> list[DecisionModel]:
    """
    Extract decision candidates from chunks and persist novel ones.

    Returns newly persisted decisions (skips exact-title duplicates).
    """
    candidates = extract_decision_candidates(chunks)
    if not candidates:
        return []

    # Check for existing decisions with the same title to avoid duplicates
    existing = await decision_repo.list_for_workspace(session, workspace_id, limit=200)
    existing_titles = {d.title.lower().strip() for d in existing}

    new_decisions: list[DecisionModel] = []
    for candidate in candidates:
        if candidate["title"].lower().strip() in existing_titles:
            logger.debug("Decision duplicate skipped: %s", candidate["title"][:60])
            continue

        decision = await decision_repo.create_decision(
            session=session,
            workspace_id=workspace_id,
            title=candidate["title"],
            description=candidate["description"],
            decided_by=candidate.get("decided_by"),
            source_event_id=candidate.get("source_event_id"),
            decision_date=datetime.now(timezone.utc),
        )
        new_decisions.append(decision)
        logger.info("New decision persisted: %s (id=%s)", decision.title[:60], decision.id)

    return new_decisions


async def get_decisions_for_workspace(
    session: AsyncSession,
    workspace_id: UUID,
    status: str | None = "ACTIVE",
) -> list[DecisionModel]:
    """
    Retrieve decisions for a workspace, optionally filtered by status.
    Used by the /api/v1/decisions endpoint.
    """
    return await decision_repo.list_for_workspace(session, workspace_id, status=status)
