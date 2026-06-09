# tests/unit/ingestion/test_entity_extractor.py
# Tests for BasicEntityExtractor — no database required.
# Run: pytest tests/unit/ingestion/test_entity_extractor.py -v

import pytest

from backend.ingestion.entity_extractor import BasicEntityExtractor
from backend.models.enums import EntityType


class TestBasicEntityExtractor:
    def setup_method(self):
        # Use narrow known-entity lists so tests are isolated from constant changes
        self.extractor = BasicEntityExtractor(
            service_names=["auth-service", "payment-gateway", "shared-db"],
            team_names=["platform-team", "payments-team"],
        )

    def test_extracts_known_service(self):
        mentions = self.extractor.extract("auth-service is down")
        names = [m.name for m in mentions]
        assert "auth-service" in names

    def test_extracts_known_team(self):
        mentions = self.extractor.extract("platform-team owns this service")
        names = [m.name for m in mentions]
        assert "platform-team" in names

    def test_entity_type_is_service(self):
        mentions = self.extractor.extract("auth-service crashed")
        service_mentions = [m for m in mentions if m.name == "auth-service"]
        assert len(service_mentions) == 1
        assert service_mentions[0].entity_type == EntityType.SERVICE

    def test_entity_type_is_team(self):
        mentions = self.extractor.extract("payments-team handled the incident")
        team_mentions = [m for m in mentions if m.name == "payments-team"]
        assert len(team_mentions) == 1
        assert team_mentions[0].entity_type == EntityType.TEAM

    def test_confidence_is_1_0_for_exact_match(self):
        mentions = self.extractor.extract("auth-service is recovering")
        assert all(m.confidence == 1.0 for m in mentions)

    def test_case_insensitive_match(self):
        mentions = self.extractor.extract("AUTH-SERVICE is healthy")
        names = [m.name for m in mentions]
        assert "auth-service" in names

    def test_no_match_returns_empty_list(self):
        mentions = self.extractor.extract("Everything is fine today")
        assert mentions == []

    def test_multiple_entities_in_one_text(self):
        mentions = self.extractor.extract("auth-service is owned by platform-team")
        names = [m.name for m in mentions]
        assert "auth-service" in names
        assert "platform-team" in names

    def test_each_entity_appears_at_most_once(self):
        # "auth-service" appears twice in the text
        mentions = self.extractor.extract("auth-service failed, auth-service is now recovering")
        service_mentions = [m for m in mentions if m.name == "auth-service"]
        assert len(service_mentions) == 1

    def test_unknown_entity_is_not_extracted(self):
        mentions = self.extractor.extract("the foo-system barked at baz-team")
        assert mentions == []

    def test_payment_gateway_extracted(self):
        mentions = self.extractor.extract("payment-gateway latency spiked to 2s")
        names = [m.name for m in mentions]
        assert "payment-gateway" in names

    def test_empty_custom_lists_return_empty(self):
        extractor = BasicEntityExtractor(service_names=[], team_names=[])
        mentions = extractor.extract("auth-service is down")
        assert mentions == []
