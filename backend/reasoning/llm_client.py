# Purpose:      Abstract LLM client for final synthesis.
#               Provider-agnostic interface allowing swapping via config.
# Called By:    composer.py
# Dependencies: openai, google-generativeai, anthropic, core/config.py

import os
import httpx

from backend.core.config import get_settings

class LLMClient:
    """
    Provider-agnostic LLM interface.
    Reads from get_settings() to instantiate the correct client dynamically.
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider.lower()
        self.model = self.settings.llm_model
        self.api_key = self.settings.llm_api_key
        self.base_url = self.settings.llm_base_url
        self.temperature = self.settings.llm_temperature
        self.timeout = self.settings.llm_timeout_seconds

    async def generate_completion(self, system_prompt: str, user_prompt: str) -> str:
        """
        Calls the configured LLM provider securely.
        """
        if self.provider == "mock":
            return "Based on the provided context, the system is working as expected. [123e4567-e89b-12d3-a456-426614174000]"

        if self.provider == "openai":
            import openai
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            import anthropic
            client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            response = await client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096,
                temperature=self.temperature
            )
            return response.content[0].text

        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt
            )
            response = await model.generate_content_async(
                contents=user_prompt,
                generation_config=genai.GenerationConfig(temperature=self.temperature)
            )
            return response.text

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

llm_client = LLMClient()
