# tests/unit/ingestion/test_constants.py
# Tests for ingestion/constants.py — no DB, no I/O.
# Run: pytest tests/unit/ingestion/test_constants.py -v

from backend.ingestion.constants import (
    KNOWN_SERVICE_NAMES,
    KNOWN_TEAM_NAMES,
    SOURCE_AUTHORITY_MAP,
)
from backend.models.enums import SourceType


class TestSourceAuthorityMap:
    def test_authority_map_is_not_empty(self):
        assert len(SOURCE_AUTHORITY_MAP) > 0

    def test_all_scores_are_floats_in_range(self):
        for key, score in SOURCE_AUTHORITY_MAP.items():
            assert isinstance(score, float), f"{key} score must be float"
            assert 0.0 <= score <= 1.0, f"{key} score {score} is out of range"

    def test_adr_has_highest_authority(self):
        assert SOURCE_AUTHORITY_MAP["adr"] == 1.00

    def test_slack_has_lowest_authority(self):
        slack_score = SOURCE_AUTHORITY_MAP["slack"]
        for key, score in SOURCE_AUTHORITY_MAP.items():
            if key != "slack":
                assert score >= slack_score, f"{key} ({score}) should be >= slack ({slack_score})"

    def test_incident_authority_is_0_90(self):
        assert SOURCE_AUTHORITY_MAP["incident"] == 0.90

    def test_jira_authority_is_0_80(self):
        assert SOURCE_AUTHORITY_MAP["jira"] == 0.80

    def test_github_authority_is_0_75(self):
        assert SOURCE_AUTHORITY_MAP["github"] == 0.75

    def test_slack_authority_is_0_60(self):
        assert SOURCE_AUTHORITY_MAP["slack"] == 0.60


class TestKnownEntityLists:
    def test_service_names_is_not_empty(self):
        assert len(KNOWN_SERVICE_NAMES) > 0

    def test_team_names_is_not_empty(self):
        assert len(KNOWN_TEAM_NAMES) > 0

    def test_auth_service_in_service_names(self):
        assert "auth-service" in KNOWN_SERVICE_NAMES

    def test_payment_gateway_in_service_names(self):
        assert "payment-gateway" in KNOWN_SERVICE_NAMES

    def test_platform_team_in_team_names(self):
        assert "platform-team" in KNOWN_TEAM_NAMES

    def test_all_service_names_are_non_empty_strings(self):
        for name in KNOWN_SERVICE_NAMES:
            assert isinstance(name, str) and name.strip(), f"Invalid service name: {repr(name)}"

    def test_all_team_names_are_non_empty_strings(self):
        for name in KNOWN_TEAM_NAMES:
            assert isinstance(name, str) and name.strip(), f"Invalid team name: {repr(name)}"

    def test_no_duplicate_service_names(self):
        assert len(KNOWN_SERVICE_NAMES) == len(set(KNOWN_SERVICE_NAMES))

    def test_no_duplicate_team_names(self):
        assert len(KNOWN_TEAM_NAMES) == len(set(KNOWN_TEAM_NAMES))
