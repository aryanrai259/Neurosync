# Purpose:      Module-level constants for the ingestion pipeline.
#               Central place for authority scores and known entity seed lists.
#               Import from here — never hardcode these values elsewhere.
# Called By:    ingestion/worker.py, ingestion/entity_extractor.py
# Calls:        nothing
# Dependencies: none

# ---------------------------------------------------------------------------
# Authority scores per source type.
# Used when storing events and computing retrieval confidence.
# Higher = more authoritative. ADRs are ground truth; Slack is weakest.
# ---------------------------------------------------------------------------
SOURCE_AUTHORITY_MAP: dict[str, float] = {
    "adr":      1.00,
    "incident": 0.90,
    "jira":     0.80,
    "github":   0.75,
    "slack":    0.60,
}

# ---------------------------------------------------------------------------
# Seed entity name lists for BasicEntityExtractor.
# Phase 3: regex + exact-match against these lists.
# Phase 5+: replaced by a DB-backed lookup from entity_registry.
# ---------------------------------------------------------------------------

# AcmeCloud services (from the synthetic dataset spec)
KNOWN_SERVICE_NAMES: list[str] = [
    "auth-service",
    "payment-gateway",
    "user-directory",
    "ledger-service",
    "fraud-detector",
    "shared-db",
    "notification-service",
    "api-router",
    "redis-cluster",
    "k8s-cluster",
]

# AcmeCloud teams
KNOWN_TEAM_NAMES: list[str] = [
    "platform-team",
    "payments-team",
    "identity-team",
    "frontend-team",
    "sre-team",
    "data-ml-team",
]
