# Synthetic Data & Demo Design: Company Brain

Version: 1.0
Status: Dataset Specification
Parent Document: Company Brain Final Master Architecture v2.1

## 1. Dataset Generator Spec

To make the demo credible, the synthetic dataset must have sufficient density. The generator should target:

| Entity Type | Count | Notes |
| :--- | :---: | :--- |
| Teams | 10 | Platform, Payments, Identity, Frontend, SRE, etc. |
| Employees | 50 | Roles: Eng, PM, Lead, Architect. |
| Services | 20 | auth-service, payment-gateway, api-router, etc. |
| Tickets (Jira) | 100 | Bugs, Features, Tasks. |
| Slack Messages| 500 | Threaded conversations, emoji reactions. |
| GitHub PRs | 100 | Descriptions, comments, reviewers. |
| Incidents | 30 | Postmortems linked to services and teams. |
| Decisions | 20 | Explicit ADRs and architectural pivots. |

## 2. Demo Scenario: "AcmeCloud"

**Company Name:** AcmeCloud (A mid-sized Fintech SaaS)

### Core Teams & Services
- **Platform Team:** Owns `k8s-cluster`, `shared-db`.
- **Payments Team:** Owns `payment-gateway`, `ledger-service`.
- **Identity Team:** Owns `auth-service`, `user-directory`.

### Sample Narrative Incident
**Event:** `auth-service` outage (2025-03-01)
- **Cause:** Token refresh bug during high load.
- **Evidence:**
    - Slack: "Is auth down for everyone?"
    - GitHub: PR #442 "Fix: increase token TTL".
    - Decision: "Migrate to Redis for token storage to handle persistence better."

### Sample Queries the System Must Handle
1.  **"Who is the current owner of the payment-gateway?"**
    - *Expected Path:* Graph search (`Service {name: 'payment-gateway'}<-[:OWNS]-(Team)`).
2.  **"Why did we move to Redis for the auth-service?"**
    - *Expected Path:* Decision lookup + Vector search in PRs.
3.  **"Show me a timeline of changes for the Identity team last month."**
    - *Expected Path:* Temporal relational search filtered by team members.
4.  **"What services will be affected if the shared-db goes down?"**
    - *Expected Path:* Graph traversal (`Service {name: 'shared-db'}<-[:DEPENDS_ON*]-(Service)`).

## 3. Dataset Integrity Rules
- **Temporal Consistency:** Events must happen in a logical order (e.g., a bug is reported before it is fixed).
- **Entity Stability:** A person's email must remain constant across Slack and GitHub.
- **Relationship Density:** Every service must have at least one owning team and 1-3 upstream dependencies.
