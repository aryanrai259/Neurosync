# Purpose:      Orchestrator for the entire Reasoning Phase 5 pipeline.
# Called By:    api/v1/reasoning.py
# Dependencies: classifier, planner, composer, citation

import time
from uuid import UUID, uuid4

from backend.reasoning.classifier import classifier
from backend.reasoning.schemas import GroundedAnswer
from backend.reasoning.planner import planner
from backend.reasoning.composer import composer
from backend.reasoning.citation import citation_validator
from backend.db.session import async_session
from backend.db.repositories.config_repo import config_repo


class ReasoningPipeline:
    """Orchestrates the Reasoning Layer single-pass workflow."""

    async def query(self, query_str: str, workspace_id: UUID) -> GroundedAnswer:
        """
        Full end-to-end trace:
        1. Classify Intent
        2. Plan Retrieval
        3. Retrieve (Mocked here for structural shell)
        4. Synthesize
        5. Validate Citations
        """
        start_ms = int(time.time() * 1000)
        query_id = uuid4()

        # 1. Classify
        # Fetch known_entities dynamically from the authoritative Config Registry
        async with async_session() as session:
            known_entities = await config_repo.get_known_entities(session, workspace_id)
            
        intent = classifier.classify(query_str, known_entities)

        # 2. Plan
        plan = planner.plan(intent)

        # 3. Retrieve
        # This calls the Phase 4 Hybrid Retriever. Mocked payload for shell.
        mock_retrieved_chunks = [
            {"id": "123e4567-e89b-12d3-a456-426614174000", "content": "Auth service is owned by Platform Team."},
        ]

        # 4. Synthesize
        answer, proposed_citations = await composer.synthesize(query_str, plan, mock_retrieved_chunks)

        # 5. Validate Citations
        validated_cites, confidence = citation_validator.validate(proposed_citations, mock_retrieved_chunks)

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
