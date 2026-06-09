# Purpose:      Orchestrator for the entire Reasoning Phase 5 pipeline.
# Called By:    api/v1/reasoning.py
# Dependencies: classifier, planner, composer, citation

import asyncio
import logging
import time
from uuid import UUID, uuid4

from backend.reasoning.classifier import classifier
from backend.reasoning.schemas import GroundedAnswer, RetrievalTrace
from backend.reasoning.planner import planner
from backend.reasoning.composer import composer
from backend.reasoning.citation import citation_validator
from backend.reasoning.decision_module import extract_and_persist_decisions
from backend.db.session import async_session
from backend.db.repositories.config_repo import config_repo
from backend.db.repositories.vector_repo import vector_repo
from backend.graph.client import get_driver
from backend.retrieval.vector_search import vector_search
from backend.retrieval.graph_search import graph_search
from backend.retrieval import hybrid

logger = logging.getLogger(__name__)


class ReasoningPipeline:
    """Orchestrates the Reasoning Layer single-pass workflow."""

    async def query(self, query_str: str, workspace_id: UUID) -> GroundedAnswer:
        """
        Full end-to-end trace:
        1. Classify Intent
        2. Plan Retrieval
        3. Retrieve (Concurrent Graph + Vector execution)
        4. Synthesize
        5. Validate Citations
        """
        start_ms = int(time.time() * 1000)
        query_id = uuid4()

        # 1. Classify
        async with async_session() as session:
            known_entities = await config_repo.get_known_entities(session, workspace_id)
            
        intent = classifier.classify(query_str, known_entities)

        # 2. Plan
        plan = planner.plan(intent)

        # 3. Retrieve
        retrieval_start = int(time.time() * 1000)
        vector_ms = 0
        graph_ms = 0

        async with async_session() as session:
            driver = get_driver()
            
            async def run_vector():
                nonlocal vector_ms
                t0 = int(time.time() * 1000)
                try:
                    res = await vector_search(session, vector_repo, workspace_id, query_str, k=plan.max_vector_results)
                except Exception as e:
                    logger.error("Vector search failed: %s", e)
                    res = []
                vector_ms = int(time.time() * 1000) - t0
                return res

            async def run_graph():
                nonlocal graph_ms
                t0 = int(time.time() * 1000)
                try:
                    res = await graph_search(session, driver, workspace_id, query_str, k=plan.max_graph_results)
                except Exception as e:
                    logger.error("Graph search failed: %s", e)
                    res = []
                graph_ms = int(time.time() * 1000) - t0
                return res

            tasks = []
            if plan.strategy in ("VECTOR_ONLY", "HYBRID"):
                tasks.append(run_vector())
            else:
                tasks.append(asyncio.sleep(0, result=[]))

            if plan.strategy in ("GRAPH_ONLY", "HYBRID"):
                tasks.append(run_graph())
            else:
                tasks.append(asyncio.sleep(0, result=[]))

            vector_chunks, graph_chunks = await asyncio.gather(*tasks)

        merged_chunks = hybrid.merge(vector_chunks, graph_chunks, k=max(plan.max_vector_results, plan.max_graph_results))
        retrieval_ms = int(time.time() * 1000) - retrieval_start

        # Emit Observability Trace
        trace = RetrievalTrace(
            strategy=plan.strategy,
            vector_results_count=len(vector_chunks),
            graph_results_count=len(graph_chunks),
            merged_results_count=len(merged_chunks),
            retrieval_ms=retrieval_ms,
            vector_ms=vector_ms,
            graph_ms=graph_ms
        )
        logger.info("Retrieval execution trace", extra={"retrieval_trace": trace.model_dump()})

        # Fail closed
        if not merged_chunks:
            end_ms = int(time.time() * 1000)
            return GroundedAnswer(
                query_id=query_id,
                answer_markdown="No supporting evidence found.",
                retrieval_strategy=plan.strategy,
                citations=[],
                confidence="LOW",
                execution_ms=end_ms - start_ms,
            )

        # 4. Synthesize
        answer, proposed_citations = await composer.synthesize(query_str, plan, merged_chunks)

        # 5. Validate Citations
        validated_cites, confidence = citation_validator.validate(proposed_citations, merged_chunks)

        # 6. Auto-extract decisions from retrieved context
        try:
            async with async_session() as _dec_session:
                await extract_and_persist_decisions(_dec_session, workspace_id, merged_chunks)
        except Exception as _dec_exc:
            logger.warning("Decision auto-extraction failed (non-fatal): %s", _dec_exc)

        end_ms = int(time.time() * 1000)

        return GroundedAnswer(
            query_id=query_id,
            answer_markdown=answer,
            retrieval_strategy=plan.strategy,
            citations=[UUID(c) for c in validated_cites],
            confidence=confidence,
            execution_ms=end_ms - start_ms,
        )

pipeline = ReasoningPipeline()

