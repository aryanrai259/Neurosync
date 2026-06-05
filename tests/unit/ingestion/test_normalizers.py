# tests/unit/ingestion/test_normalizers.py
# Tests for SlackNormalizer, GithubNormalizer, JiraNormalizer.
# These tests require no database — all assertions are on Python objects.
# Run: pytest tests/unit/ingestion/test_normalizers.py -v

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.ingestion.normalizers.github import GithubNormalizer
from backend.ingestion.normalizers.jira import JiraNormalizer
from backend.ingestion.normalizers.slack import SlackNormalizer
from backend.ingestion.schemas import RawEvent
from backend.models.enums import SourceType

WORKSPACE_ID = uuid4()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_slack_event(**overrides) -> RawEvent:
    defaults = dict(
        source=SourceType.SLACK,
        source_id="1716000000.000001",
        raw_content="auth-service is down again",
        raw_author="alice",
        raw_timestamp="2025-01-15T14:22:00Z",
        extra={"channel": "incidents"},
    )
    return RawEvent(**{**defaults, **overrides})


def make_github_event(**overrides) -> RawEvent:
    defaults = dict(
        source=SourceType.GITHUB,
        source_id="pr-42",
        raw_content="Moved auth tokens to Redis for horizontal scaling.",
        raw_author="bob",
        raw_timestamp="2025-01-20T09:00:00Z",
        extra={
            "repo": "auth-service",
            "pr_number": 42,
            "title": "Switch session store to Redis",
            "labels": ["architecture"],
        },
    )
    return RawEvent(**{**defaults, **overrides})


def make_jira_event(**overrides) -> RawEvent:
    defaults = dict(
        source=SourceType.JIRA,
        source_id="PROJ-1234",
        raw_content="Auth service is returning 500 errors on login after the Redis migration.",
        raw_author="charlie",
        raw_timestamp="2025-01-21T11:30:00Z",
        extra={"summary": "Auth service 500 errors post-migration", "priority": "HIGH"},
    )
    return RawEvent(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# SlackNormalizer
# ---------------------------------------------------------------------------


class TestSlackNormalizer:
    def setup_method(self):
        self.normalizer = SlackNormalizer()

    def test_source_type_is_slack(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.source == SourceType.SLACK

    def test_workspace_id_is_preserved(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.workspace_id == WORKSPACE_ID

    def test_source_id_preserved(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.source_id == "1716000000.000001"

    def test_author_id_is_raw_author(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.author_id == "alice"

    def test_timestamp_is_timezone_aware(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.timestamp.tzinfo is not None

    def test_timestamp_value_correct(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        expected = datetime(2025, 1, 15, 14, 22, 0, tzinfo=timezone.utc)
        assert event.timestamp == expected

    def test_slack_has_no_title(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title is None

    def test_content_is_cleaned(self):
        raw = make_slack_event(raw_content="auth-service is down again")
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.content == "auth-service is down again"

    def test_mention_markup_stripped(self):
        raw = make_slack_event(raw_content="<@U123> deployed auth-service")
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert "<@" not in event.content
        assert "@user" in event.content

    def test_channel_mention_stripped(self):
        raw = make_slack_event(raw_content="posted in <#C123|incidents>")
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert "<#" not in event.content
        assert "#incidents" in event.content

    def test_authority_score_in_metadata(self):
        raw = make_slack_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["authority_score"] == 0.60

    def test_extra_fields_carried_into_metadata(self):
        raw = make_slack_event(extra={"channel": "incidents", "thread_ts": "1716000001.000002"})
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["channel"] == "incidents"
        assert event.metadata["thread_ts"] == "1716000001.000002"


# ---------------------------------------------------------------------------
# GithubNormalizer
# ---------------------------------------------------------------------------


class TestGithubNormalizer:
    def setup_method(self):
        self.normalizer = GithubNormalizer()

    def test_source_type_is_github(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.source == SourceType.GITHUB

    def test_title_built_from_pr_number_and_repo(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title == "[auth-service] PR #42: Switch session store to Redis"

    def test_title_built_from_issue_number(self):
        raw = make_github_event(
            extra={"repo": "auth-service", "issue_number": 7, "title": "Fix auth bug"}
        )
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title == "[auth-service] Issue #7: Fix auth bug"

    def test_title_is_none_when_no_extra_provided(self):
        raw = make_github_event(extra={})
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title is None

    def test_content_unchanged(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.content == raw.raw_content

    def test_authority_score_in_metadata(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["authority_score"] == 0.75

    def test_timestamp_is_timezone_aware(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.timestamp.tzinfo is not None

    def test_labels_carried_into_metadata(self):
        raw = make_github_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["labels"] == ["architecture"]


# ---------------------------------------------------------------------------
# JiraNormalizer
# ---------------------------------------------------------------------------


class TestJiraNormalizer:
    def setup_method(self):
        self.normalizer = JiraNormalizer()

    def test_source_type_is_jira(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.source == SourceType.JIRA

    def test_title_built_from_key_and_summary(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title == "PROJ-1234: Auth service 500 errors post-migration"

    def test_title_is_key_only_when_no_summary(self):
        raw = make_jira_event(extra={})
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.title == "PROJ-1234"

    def test_content_unchanged(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.content == raw.raw_content

    def test_authority_score_in_metadata(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["authority_score"] == 0.80

    def test_timestamp_is_timezone_aware(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.timestamp.tzinfo is not None

    def test_priority_carried_into_metadata(self):
        raw = make_jira_event()
        event = self.normalizer.normalize(raw, WORKSPACE_ID)
        assert event.metadata["priority"] == "HIGH"
