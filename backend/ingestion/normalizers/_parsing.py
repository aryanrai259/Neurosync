# Purpose:      Shared timestamp parsing utility used by all normalizers.
#               Isolated here so each normalizer does not duplicate this logic.
# Called By:    ingestion/normalizers/slack.py, github.py, jira.py
# Calls:        nothing
# Dependencies: python stdlib (datetime, re)

import re
from datetime import datetime, timezone


def parse_iso_timestamp(raw: str) -> datetime:
    """
    Parse an ISO 8601 timestamp string to a timezone-aware datetime.

    Handles the common case of trailing 'Z' (which Python's fromisoformat
    does not accept before 3.11) and naive datetimes (assumes UTC).

    Raises ValueError if the string cannot be parsed.
    """
    # Replace trailing Z with +00:00 for broad Python 3.10 compatibility
    normalised = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalised)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def strip_slack_mentions(text: str) -> str:
    """
    Remove Slack mention markup from message text.

    Slack encodes user mentions as <@U12345> and channel mentions as
    <#C12345|general>. We replace them with readable placeholders so
    the normalised content is clean text for embedding.

    Examples:
        "<@U123> is working on auth-service" → "@user is working on auth-service"
        "<#C123|general> discussion"         → "#general discussion"
    """
    # <@UXXXXXXX> → @user
    text = re.sub(r"<@[A-Z0-9]+>", "@user", text)
    # <#CXXXXXXX|channel-name> → #channel-name
    text = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", text)
    return text.strip()
