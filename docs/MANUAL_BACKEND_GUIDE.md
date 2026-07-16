# Manual Backend Experience Guide
**For Aryan**

This guide provides everything you need to manually experience the backend capabilities (Phase 0-6 + 8) end-to-end. Follow the sections sequentially for a smooth walkthrough.

> **2026-07-16 update:** Running this guide live earlier today surfaced 3 bugs — the reasoning query in step 8 returned "No supporting evidence found," the decisions in step 10 were empty, and the timeline in step 11 500'd. **All three are now fixed and re-verified live** — see `docs/current/CURRENT_STATE.md` §1 for the writeup. The connection details and `evaluate.py` command below have also been corrected to match the actual `docker-compose.yml` and script signature.

---

## 1. Environment Startup

You need PostgreSQL (with pgvector), Neo4j, and the API running.

1. **Environment Variables (`.env`)**
   Make sure your `.env` contains at minimum:
   ```env
   # Database URLs — match docker-compose.yml's actual port mapping (5433 on host)
   DATABASE_URL=postgresql+asyncpg://neuro_user:neuro_password@127.0.0.1:5433/neuro_db
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=neuro_password

   # LLM Configuration (for Reasoning layer)
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-2.5-pro
   LLM_API_KEY=your_gemini_api_key_here

   # Embeddings (Ensure Ollama is running)
   EMBEDDING_MODEL=nomic-embed-text
   ```

2. **Start Infrastructure**
   ```bash
   docker compose up -d
   ```

3. **Run Migrations**
   ```bash
   python -m alembic upgrade head
   ```

4. **Start the API Server**
   ```bash
   uvicorn backend.main:app --reload
   ```

---

## 2. Workspace Creation

Workspaces partition all data. This is a public endpoint.

```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "Aryan Test Workspace", "slug": "aryan-test"}'
```

*Note the `id` returned (e.g., `123e4567-e89b-12d3-a456-426614174000`). We will use it below as `<WORKSPACE_ID>`.*

---

## 3. API Key Generation

Keys are bound to a workspace. Generating a key gives you a one-time raw key.

```bash
curl -X POST http://localhost:8000/api/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "<WORKSPACE_ID>", "label": "Aryan CLI Key"}'
```

*Note the `raw_key` returned (e.g., `cb_XXXXX...`). We will use it below as `<API_KEY>`.*

---

## 4. Authentication Verification

Let's prove the endpoint is protected by hitting a protected route *without* the key:

```bash
curl -i -X POST http://localhost:8000/api/v1/ingest/synthetic \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "<WORKSPACE_ID>", "requested_by": "aryan", "events": []}'
```
*Expected output: `HTTP/1.1 401 Unauthorized`*

---

## 5. Synthetic Ingestion Demo

Now let's use the key to ingest some knowledge.

```bash
curl -X POST http://localhost:8000/api/v1/ingest/synthetic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
  "workspace_id": "<WORKSPACE_ID>",
  "requested_by": "aryan",
  "events": [
    {
      "source": "slack",
      "source_id": "msg-001",
      "raw_content": "We decided to migrate the auth-service from Express to Go. It is now maintained by the Platform Team.",
      "raw_author": "aryan",
      "raw_timestamp": "2026-06-09T10:00:00Z"
    },
    {
      "source": "slack",
      "source_id": "msg-002",
      "raw_content": "The auth-service is failing because it depends on user-service which had a bad deployment.",
      "raw_author": "jane",
      "raw_timestamp": "2026-06-09T10:05:00Z"
    }
  ]
}'
```

*Note the `job_id` returned.*

---

## 6. GitHub Ingestion Demo

Ingest a real GitHub repository (fetches recent issues and PRs).

```bash
curl -X POST http://localhost:8000/api/v1/ingest/github \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
  "workspace_id": "<WORKSPACE_ID>",
  "requested_by": "aryan",
  "repo": "aryanrai259/Neurosync"
}'
```

*Note the `job_id` returned.*

---

## 7. Job Tracking Demo

Wait a few seconds for the background worker to process the events, extract entities/graph edges, and embed the chunks. Track the job status:

```bash
curl -s http://localhost:8000/api/v1/jobs/<JOB_ID> | json_pp
```
*Wait until `status` is `"completed"`.*

---

## 8. Reasoning Demo

Query the system. We can ask different types of questions to test the planner.

**Ownership / Architecture Query:**
```bash
curl -X POST http://localhost:8000/api/v1/reasoning/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
  "workspace_id": "<WORKSPACE_ID>",
  "query": "Who maintains the auth-service and what language is it written in?"
}'
```

**Incident Query:**
```bash
curl -X POST http://localhost:8000/api/v1/reasoning/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
  "workspace_id": "<WORKSPACE_ID>",
  "query": "Why was the auth-service failing?"
}'
```

---

## 9. Hybrid Retrieval Proof

To see *how* the system found the answer (the exact chunks retrieved from PostgreSQL and Neo4j), use the `/explain` endpoint.

```bash
curl -X POST http://localhost:8000/api/v1/reasoning/explain \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
  "workspace_id": "<WORKSPACE_ID>",
  "query": "Why was the auth-service failing?"
}'
```

*In the response, look at:*
* `"retrieval_trace"`: Shows how many chunks came from the Vector DB vs Graph DB.
* `"merged_chunks"`: The raw context fed to the LLM.

---

## 10. Decision Intelligence Demo

Because we ingested the text "We decided to migrate the auth-service", the pipeline auto-extracted that decision! Let's inspect it.

**Inspect Stored Decisions:**
```bash
curl -X GET http://localhost:8000/api/v1/decisions/<WORKSPACE_ID>
```

**Supersede a Decision:**
Take the `id` from the above output and supersede it.
```bash
curl -X POST http://localhost:8000/api/v1/decisions/single/<DECISION_ID>/supersede \
  -H "Content-Type: application/json" \
  -d '{"superseded_by": "Reverted back to Express for stability."}'
```

---

## 11. Timeline Intelligence Demo

We can ask the Timeline API to show us everything that happened to an entity (like "auth-service").

First, find the entity ID for "auth-service" from your database or config endpoints. If you know the UUID:

```bash
curl -X GET http://localhost:8000/api/v1/timeline/<WORKSPACE_ID>/entity/<ENTITY_ID>
```
*This returns a chronologically sorted list of all events referencing that entity.*

To get an LLM summary of its timeline:
```bash
curl -X GET http://localhost:8000/api/v1/timeline/<WORKSPACE_ID>/entity/<ENTITY_ID>/summary
```

---

## 12. Observability Demo

The backend automatically tracks metrics and latency for every endpoint.

**Inspect Metrics:**
```bash
curl -X GET http://localhost:8000/api/v1/metrics
```
*Notice `uptime_seconds`, `active_tasks`, and the breakdown of memory/GC.*

**Inspect Health/Latency Summary:**
```bash
curl -X GET http://localhost:8000/api/v1/metrics/health-summary
```
*Look for `requests_total`, `error_rate`, and the `p50`, `p95`, `p99` latency numbers for the endpoints you just called.*

---

## 13. Evaluation Demo

The evaluation framework automatically queries the system against a golden dataset to score retrieval accuracy and latency.

Make sure Ollama and Gemini are running/configured, then run:

```bash
set PYTHONPATH=.
python scripts/evaluate.py --workspace-id <WORKSPACE_ID>
```

*This will output a pass/fail matrix, average latencies, confidence distributions, and strategy distributions for all 10 golden queries. `--workspace-id` is required. As of 2026-07-16, this correctly reports 0/10 passing on a live-ingested workspace due to the ingestion bug described at the top of this guide.*

---

## 14. Admin Endpoints

Need to start fresh or rebuild the graph?

**Reindex Vectors & Graph (Non-destructive to events):**
```bash
curl -X POST http://localhost:8000/api/v1/admin/reindex/<WORKSPACE_ID> \
  -H "X-API-Key: <API_KEY>"
```

**Reset Workspace (Destructive):**
```bash
curl -X POST http://localhost:8000/api/v1/admin/reset/<WORKSPACE_ID> \
  -H "X-API-Key: <API_KEY>"
```

---

## 15. Full System Walkthrough (Start-to-Finish)

If you want the fastest "Aha!" moment:

1. `curl -X POST http://localhost:8000/api/v1/workspaces -d '{"name": "E2E"}'` -> *Get ID*
2. `curl -X POST http://localhost:8000/api/v1/auth/keys -d '{"workspace_id": "<ID>"}'` -> *Get Key*
3. `curl -H "X-API-Key: <KEY>" -d '{"workspace_id":"<ID>","repo":"aryanrai259/Neurosync"}' http://localhost:8000/api/v1/ingest/github`
4. Wait 30 seconds for processing.
5. `curl -H "X-API-Key: <KEY>" -d '{"workspace_id":"<ID>","query":"What is the core reasoning pipeline?"}' http://localhost:8000/api/v1/reasoning/query`
6. `curl http://localhost:8000/api/v1/metrics/health-summary` to see how fast it was.
