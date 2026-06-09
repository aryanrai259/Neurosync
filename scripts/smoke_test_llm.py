"""
Phase 5 Real LLM Smoke Test
---------------------------
Runs a real query against the configured LLM provider to prove agnosticism.
Ensure you have set LLM_PROVIDER, LLM_MODEL, and LLM_API_KEY in .env.
"""

import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings
from backend.reasoning.llm_client import llm_client

async def main():
    settings = get_settings()
    print("========================================")
    print("Phase 5 Real LLM Smoke Test")
    print("========================================")
    print(f"Provider : {settings.llm_provider}")
    print(f"Model    : {settings.llm_model}")
    print(f"Has Key? : {'Yes' if settings.llm_api_key else 'No'}")
    
    if not settings.llm_api_key and settings.llm_provider != "mock":
        print("\nERROR: Please set LLM_API_KEY in your .env file.")
        sys.exit(1)

    system_prompt = """
    You are an expert engineering assistant.
    Answer the user's question strictly using the provided context.
    You MUST cite your sources using the exact UUID of the event in brackets, e.g. [123e4567-e89b-12d3-a456-426614174000].
    Do not make claims unsupported by the text.
    """

    user_prompt = """
    Context:
    [
      {
        "id": "11111111-1111-1111-1111-111111111111",
        "content": "The auth-service is owned by the Platform Team. It relies on Redis for caching."
      }
    ]

    Question: Who owns the auth-service?
    """

    print("\nSending prompt to LLM...")
    try:
        response = await llm_client.generate_completion(system_prompt, user_prompt)
        print("\n----------------------------------------")
        print("LLM Response:")
        print("----------------------------------------")
        print(response)
        print("----------------------------------------")

        if "[11111111-1111-1111-1111-111111111111]" in response:
            print("\n[PASS] Citation Found! The LLM successfully followed instructions.")
        else:
            print("\n[FAIL] Missing Citation. The LLM failed to include the exact UUID bracket citation.")

        if "Platform Team" in response:
            print("[PASS] Grounded Answer. The LLM extracted the correct entity.")
        else:
            print("[FAIL] Ungrounded Answer. The LLM hallucinated or failed to answer.")

    except Exception as e:
        print(f"\n[FAIL] Error during LLM call: {e}")

if __name__ == "__main__":
    asyncio.run(main())
