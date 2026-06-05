# Purpose:      Live GitHub ingestion adapter.
#               Fetches real data (issues and PRs) from the GitHub API.
# Called By:    ingestion/worker.py
# Calls:        GitHub REST API
# Dependencies: httpx, backend/ingestion/schemas.py
# Test File:    tests/integration/ingestion/test_github_adapter.py

import logging

import httpx

from backend.core.config import get_settings
from backend.ingestion.adapters.base import BaseAdapter
from backend.ingestion.schemas import RawEvent
from backend.models.enums import SourceType

logger = logging.getLogger(__name__)


class GitHubAdapter(BaseAdapter):
    """
    Fetches issues and PRs from a specified GitHub repository.

    API: https://api.github.com/repos/{owner}/{repo}/issues
    GitHub returns both Issues and PRs from this endpoint.
    """

    def __init__(self, repo: str, limit: int = 10):
        self.repo = repo
        self.limit = limit
        self.base_url = "https://api.github.com"
        
        settings = get_settings()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if settings.github_token:
            self.headers["Authorization"] = f"Bearer {settings.github_token}"
        else:
            logger.warning("No GITHUB_TOKEN configured. Fetching unauthenticated (subject to strict rate limits).")

    async def fetch_events(self) -> list[RawEvent]:
        """
        Fetch the most recent issues/PRs and convert them to RawEvents.
        """
        url = f"{self.base_url}/repos/{self.repo}/issues"
        params = {
            "state": "all",
            "per_page": self.limit,
            "sort": "updated",
            "direction": "desc",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params, timeout=10.0)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("GitHub API error: %s %s", e.response.status_code, e.response.text)
                raise
            except httpx.RequestError as e:
                logger.error("Network error connecting to GitHub: %s", e)
                raise

            items = response.json()

        raw_events = []
        for item in items:
            is_pr = "pull_request" in item
            raw_event = RawEvent(
                source=SourceType.GITHUB,
                source_id=str(item["number"]),
                raw_content=item.get("body") or "",
                raw_author=item.get("user", {}).get("login", "unknown"),
                raw_timestamp=item.get("created_at"),
                extra={
                    "is_pr": is_pr,
                    "title": item.get("title"),
                    "url": item.get("html_url"),
                    "labels": [label["name"] for label in item.get("labels", [])],
                },
            )
            raw_events.append(raw_event)

        logger.info("Fetched %d events from GitHub %s", len(raw_events), self.repo)
        return raw_events
