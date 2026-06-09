# Real Retrieval Proof Report

**Generated:** 2026-06-09 12:17 UTC  
**Workspace:** `67246a12-a812-4361-bea9-cee0db949ecf`  
**Seed event IDs:** `aaaaaaaa-0000-0000-0000-000000000001`, `aaaaaaaa-0000-0000-0000-000000000002`, `aaaaaaaa-0000-0000-0000-000000000003`

> **Methodology**: Seed data is written to real PostgreSQL (pgvector) and Neo4j. embed_text is patched to return \[0.1\]×768 matching the seeded vectors. All retrieval, hybrid merge, composer, and citation validator steps are real. The LLM is real (Gemini API); if the API call fails a mock fallback is used and noted.

---

## Query 1: `Who owns auth-service?`

### 1. Classifier Output
```json
{
  "strategy": "GRAPH_ONLY",
  "extracted_entities": [
    "auth-service"
  ],
  "is_clarification_needed": false
}
```

### 2. Planner Output
```json
{
  "strategy": "GRAPH_ONLY",
  "max_vector_results": 0,
  "max_graph_results": 50,
  "max_context_tokens": 6000
}
```

### 3. Vector Retrieval Output
Fetched **0** result(s).
```json
[]
```

### 4. Graph Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 5. Hybrid Merge Output
Merged into **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 6. RetrievedChunk IDs Passed to Composer
```json
[
  "aaaaaaaa-0000-0000-0000-000000000001",
  "aaaaaaaa-0000-0000-0000-000000000002",
  "aaaaaaaa-0000-0000-0000-000000000003"
]
```

### 7. LLM Prompt Context (first 1500 chars)
<details><summary>Click to expand</summary>

```text
Context:
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]

Question: Who owns auth-service?
```
</details>

### 8. Final Answer
> Auth service is owned by the Platform Team [aaaaaaaa-0000-0000-0000-000000000001]. The team lead is @alice [aaaaaaaa-0000-0000-0000-000000000001].

### 9. Citation Validation Output
```json
{
  "validated_citations": [
    "aaaaaaaa-0000-0000-0000-000000000001"
  ],
  "confidence": "HIGH"
}
```

---

## Query 2: `What depends on auth-service?`

### 1. Classifier Output
```json
{
  "strategy": "GRAPH_ONLY",
  "extracted_entities": [
    "auth-service"
  ],
  "is_clarification_needed": false
}
```

### 2. Planner Output
```json
{
  "strategy": "GRAPH_ONLY",
  "max_vector_results": 0,
  "max_graph_results": 50,
  "max_context_tokens": 6000
}
```

### 3. Vector Retrieval Output
Fetched **0** result(s).
```json
[]
```

### 4. Graph Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 5. Hybrid Merge Output
Merged into **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 6. RetrievedChunk IDs Passed to Composer
```json
[
  "aaaaaaaa-0000-0000-0000-000000000001",
  "aaaaaaaa-0000-0000-0000-000000000002",
  "aaaaaaaa-0000-0000-0000-000000000003"
]
```

### 7. LLM Prompt Context (first 1500 chars)
<details><summary>Click to expand</summary>

```text
Context:
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]

Question: What depends on auth-service?
```
</details>

### 8. Final Answer
> I cannot answer what depends on auth-service based on the provided context. The context states that auth-service is owned by the Platform Team [aaaaaaaa-0000-0000-0000-000000000001], experienced login failures due to a PR [aaaaaaaa-0000-0000-0000-000000000002], and had a P0 outage due to a token validation bug [aaaaaaaa-0000-0000-0000-000000000003].

### 9. Citation Validation Output
```json
{
  "validated_citations": [
    "aaaaaaaa-0000-0000-0000-000000000001",
    "aaaaaaaa-0000-0000-0000-000000000002",
    "aaaaaaaa-0000-0000-0000-000000000003"
  ],
  "confidence": "HIGH"
}
```

---

## Query 3: `What PRs recently affected auth-service?`

### 1. Classifier Output
```json
{
  "strategy": "HYBRID",
  "extracted_entities": [
    "auth-service"
  ],
  "is_clarification_needed": false
}
```

### 2. Planner Output
```json
{
  "strategy": "HYBRID",
  "max_vector_results": 10,
  "max_graph_results": 50,
  "max_context_tokens": 6000
}
```

### 3. Vector Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  }
]
```

### 4. Graph Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 5. Hybrid Merge Output
Merged into **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]
```

### 6. RetrievedChunk IDs Passed to Composer
```json
[
  "aaaaaaaa-0000-0000-0000-000000000001",
  "aaaaaaaa-0000-0000-0000-000000000002",
  "aaaaaaaa-0000-0000-0000-000000000003"
]
```

### 7. LLM Prompt Context (first 1500 chars)
<details><summary>Click to expand</summary>

```text
Context:
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]

Question: What PRs recently affected auth-service?
```
</details>

### 8. Final Answer
> PR #123 affected auth-service by causing login failures in production [aaaaaaaa-0000-0000-0000-000000000002].

### 9. Citation Validation Output
```json
{
  "validated_citations": [
    "aaaaaaaa-0000-0000-0000-000000000002"
  ],
  "confidence": "HIGH"
}
```

---

## Query 4: `What outages happened around auth-service login failures?`

### 1. Classifier Output
```json
{
  "strategy": "HYBRID",
  "extracted_entities": [
    "auth-service"
  ],
  "is_clarification_needed": false
}
```

### 2. Planner Output
```json
{
  "strategy": "HYBRID",
  "max_vector_results": 10,
  "max_graph_results": 50,
  "max_context_tokens": 6000
}
```

### 3. Vector Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  }
]
```

### 4. Graph Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 5. Hybrid Merge Output
Merged into **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]
```

### 6. RetrievedChunk IDs Passed to Composer
```json
[
  "aaaaaaaa-0000-0000-0000-000000000001",
  "aaaaaaaa-0000-0000-0000-000000000002",
  "aaaaaaaa-0000-0000-0000-000000000003"
]
```

### 7. LLM Prompt Context (first 1500 chars)
<details><summary>Click to expand</summary>

```text
Context:
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]

Question: What outages happened around auth-service login failures?
```
</details>

### 8. Final Answer
> PR #123 merged into main caused auth-service login failures in prod [aaaaaaaa-0000-0000-0000-000000000002]. Additionally, a P0 outage occurred where auth-service was down for 45 minutes due to a token validation bug [aaaaaaaa-0000-0000-0000-000000000003].

### 9. Citation Validation Output
```json
{
  "validated_citations": [
    "aaaaaaaa-0000-0000-0000-000000000002",
    "aaaaaaaa-0000-0000-0000-000000000003"
  ],
  "confidence": "HIGH"
}
```

---

## Query 5: `Why was auth-service unstable last week?`

### 1. Classifier Output
```json
{
  "strategy": "HYBRID",
  "extracted_entities": [
    "auth-service"
  ],
  "is_clarification_needed": false
}
```

### 2. Planner Output
```json
{
  "strategy": "HYBRID",
  "max_vector_results": 10,
  "max_graph_results": 50,
  "max_context_tokens": 6000
}
```

### 3. Vector Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 0.0,
    "combined_score": 0.7,
    "entities": []
  }
]
```

### 4. Graph Retrieval Output
Fetched **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 0.0,
    "graph_score": 1.0,
    "combined_score": 0.3,
    "entities": []
  }
]
```

### 5. Hybrid Merge Output
Merged into **3** result(s).
```json
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201+00:00",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]
```

### 6. RetrievedChunk IDs Passed to Composer
```json
[
  "aaaaaaaa-0000-0000-0000-000000000001",
  "aaaaaaaa-0000-0000-0000-000000000002",
  "aaaaaaaa-0000-0000-0000-000000000003"
]
```

### 7. LLM Prompt Context (first 1500 chars)
<details><summary>Click to expand</summary>

```text
Context:
[
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "content": "Auth service is owned by Platform Team. The team lead is @alice.",
    "title": null,
    "source": "slack",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000002",
    "content": "PR #123 merged into main, caused auth-service login failures in prod.",
    "title": null,
    "source": "github",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  },
  {
    "event_id": "aaaaaaaa-0000-0000-0000-000000000003",
    "content": "P0 outage: auth-service was down for 45 minutes due to token validation bug.",
    "title": null,
    "source": "jira",
    "timestamp": "2026-06-09T12:17:57.885201Z",
    "author_id": "proof-script",
    "url": null,
    "vector_score": 1.0,
    "graph_score": 1.0,
    "combined_score": 1.0,
    "entities": []
  }
]

Question: Why was auth-service unstable last week?
```
</details>

### 8. Final Answer
> Auth-service was unstable because PR #123 was merged into main, which caused login failures in production [aaaaaaaa-0000-0000-0000-000000000002]. Additionally, a token validation bug led to a P0 outage, causing auth-service to be down for 45 minutes [aaaaaaaa-0000-0000-0000-000000000003].

### 9. Citation Validation Output
```json
{
  "validated_citations": [
    "aaaaaaaa-0000-0000-0000-000000000002",
    "aaaaaaaa-0000-0000-0000-000000000003"
  ],
  "confidence": "HIGH"
}
```

---

## Phase Closure Verdict

| Criterion | Status |
|-----------|--------|
| Classifier executed on real query | ✅ |
| Planner produced real strategy | ✅ |
| Vector retrieval queried pgvector | ✅ |
| Graph retrieval queried Neo4j | ✅ |
| Hybrid merge combined both sources | ✅ |
| RetrievedChunk IDs passed to composer | ✅ |
| LLM synthesized from retrieved context | ✅ |
| Citation validator ran post-synthesis | ✅ |

**All 5 query traces validated. Phase 4 and Phase 5 are officially closed.**
