# Purpose:      Hydrates context and assembles LLM prompt.
# Called By:    pipeline.py
# Dependencies: llm_client.py

import json
import tiktoken

from backend.reasoning.llm_client import llm_client
from backend.reasoning.schemas import RetrievalPlan
from backend.retrieval.schemas import RetrievedChunk

SYSTEM_PROMPT = """
You are an expert engineering assistant.
You will be provided with context chunks retrieved from a knowledge graph and vector store.
Answer the user's question strictly using the provided context.
You MUST cite your sources using the exact UUID of the event in brackets, e.g. [123e4567-e89b-12d3-a456-426614174000].
Do not make claims unsupported by the text.
"""

class Composer:
    """Assembles prompt and calls LLM."""
    
    def __init__(self):
        # We use cl100k_base as a standard tokenizer approximation across providers
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def synthesize(self, query: str, plan: RetrievalPlan, retrieved_chunks: list[RetrievedChunk]) -> tuple[str, list[str]]:
        """
        Synthesizes an answer and parses out proposed citations.
        Returns (answer_markdown, proposed_citations)
        """
        # 1. Hydrate context with strict Tiktoken Budgeting
        budget = plan.max_context_tokens
        accepted_chunks = []
        current_tokens = 0
        
        for chunk in retrieved_chunks:
            chunk_str = chunk.model_dump_json()
            chunk_tokens = len(self.tokenizer.encode(chunk_str))
            
            if current_tokens + chunk_tokens <= budget:
                accepted_chunks.append(chunk.model_dump(mode="json"))
                current_tokens += chunk_tokens
            else:
                break # Drop remaining chunks to respect the strict budget
                
        context_str = json.dumps(accepted_chunks, indent=2)

        user_prompt = f"Context:\n{context_str}\n\nQuestion: {query}"

        # 2. Call LLM
        answer = await llm_client.generate_completion(SYSTEM_PROMPT, user_prompt)

        # 3. Naive citation extraction (looks for UUIDs in brackets)
        import re
        # Pattern for UUIDs in brackets e.g. [123e4567-e89b-12d3-a456-426614174000]
        uuid_pattern = r"\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]"
        proposed_citations = re.findall(uuid_pattern, answer.lower())

        return answer, proposed_citations

composer = Composer()
