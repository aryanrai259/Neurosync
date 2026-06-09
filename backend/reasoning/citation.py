# Purpose:      Citation Validation post-processor.
# Called By:    pipeline.py
# Dependencies: schemas.py

from typing import Literal
from backend.retrieval.schemas import RetrievedChunk


class CitationValidator:
    """
    Validates citations proposed by the LLM against the actual provided context.
    """

    def validate(self, proposed_citations: list[str], retrieved_chunks: list[RetrievedChunk]) -> tuple[list[str], Literal["HIGH", "MEDIUM", "LOW"]]:
        """
        Cross-references citations against valid context IDs.
        Strips hallucinated citations and downgrades confidence.
        """
        valid_ids = {str(chunk.event_id) for chunk in retrieved_chunks}
        
        validated_citations = []
        hallucinations = 0

        for cite in proposed_citations:
            if cite in valid_ids:
                validated_citations.append(cite)
            else:
                hallucinations += 1

        # Confidence logic
        if not proposed_citations:
            # Did not cite anything
            confidence = "LOW"
        elif hallucinations == 0:
            confidence = "HIGH"
        elif hallucinations > 0 and validated_citations:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # Unique the validated citations
        return list(set(validated_citations)), confidence

citation_validator = CitationValidator()
