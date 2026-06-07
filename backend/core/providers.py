import os
from pydantic import BaseModel
from typing import Optional, AsyncGenerator

try:
    from mistralai.client import Mistral
except ImportError:
    Mistral = None

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from groq import AsyncGroq

class LLMProvider:
    def __init__(self, provider_name: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider_name = provider_name
        self.model_name = model_name
        
        self.api_key = api_key
        self.base_url = base_url
        
        if self.provider_name == 'openai':
            if not self.api_key:
                raise ValueError("OpenAI API key is missing in database.")
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            
        elif self.provider_name == 'anthropic':
            if not self.api_key:
                raise ValueError("Anthropic API key is missing in database.")
            self.client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)
            
        elif self.provider_name == 'mistral':
            if not self.api_key:
                raise ValueError("Mistral API key is missing in database.")
            self.client = Mistral(api_key=self.api_key, server_url=self.base_url)
            
        elif self.provider_name == 'groq':
            if not self.api_key:
                raise ValueError("Groq API key is missing in database.")
            self.client = AsyncGroq(api_key=self.api_key, base_url=self.base_url)
            
        elif self.provider_name == 'local_ollama':
            # Local ollama via OpenAI client
            self.client = AsyncOpenAI(api_key="ollama", base_url=self.base_url or "http://host.docker.internal:11434/api")
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")

    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        if self.provider_name in ['openai', 'groq', 'local_ollama']:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        elif self.provider_name == 'anthropic':
            stream = await self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            async for event in stream:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    yield event.delta.text

        elif self.provider_name == 'mistral':
            # mistralai SDK stream is async iterable
            stream = await self.client.chat.stream_async(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            async for chunk in stream:
                if chunk.data.choices[0].delta.content is not None:
                    yield chunk.data.choices[0].delta.content

    async def generate_sync(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider_name in ['openai', 'groq', 'local_ollama']:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content or ""

        elif self.provider_name == 'anthropic':
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text

        elif self.provider_name == 'mistral':
            response = await self.client.chat.complete_async(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content or ""
