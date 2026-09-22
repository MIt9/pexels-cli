"""AI Provider implementations for Gemini, OpenAI, and Ollama."""

import json
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from pexels_cli.config import Config


T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Exception for AI Provider errors."""
    pass


class BaseAIProvider:
    """Base AI Provider interface."""

    def __init__(self, config: Config):
        self.config = config

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        raise NotImplementedError

    async def generate_structured(
        self, prompt: str, schema: Type[T], system_instruction: Optional[str] = None
    ) -> T:
        raise NotImplementedError


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider implementation."""

    def __init__(self, config: Config):
        super().__init__(config)
        if not config.gemini_api_key:
            raise AIProviderError(
                "Gemini API Key is missing. Set it via `pexels-cli config set-ai-key <KEY> --provider gemini` "
                "or set the GEMINI_API_KEY environment variable."
            )
        try:
            from google import genai
            self.client = genai.Client(api_key=config.gemini_api_key)
        except ImportError:
            raise AIProviderError("google-genai package is not installed.")

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            ) if system_instruction else None

            response = self.client.models.generate_content(
                model=self.config.gemini_model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            raise AIProviderError(f"Gemini API error: {e}")

    async def generate_structured(
        self, prompt: str, schema: Type[T], system_instruction: Optional[str] = None
    ) -> T:
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=system_instruction,
            )
            response = self.client.models.generate_content(
                model=self.config.gemini_model,
                contents=prompt,
                config=config,
            )
            text = response.text or "{}"
            return schema.model_validate_json(text)
        except Exception as e:
            raise AIProviderError(f"Gemini Structured Output error: {e}")


class OpenAIProvider(BaseAIProvider):
    """OpenAI API Provider implementation."""

    def __init__(self, config: Config):
        super().__init__(config)
        if not config.openai_api_key:
            raise AIProviderError(
                "OpenAI API Key is missing. Set it via `pexels-cli config set-ai-key <KEY> --provider openai` "
                "or set the OPENAI_API_KEY environment variable."
            )
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url or None,
            )
        except ImportError:
            raise AIProviderError("openai package is not installed.")

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise AIProviderError(f"OpenAI API error: {e}")

    async def generate_structured(
        self, prompt: str, schema: Type[T], system_instruction: Optional[str] = None
    ) -> T:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({
                "role": "user",
                "content": f"{prompt}\nReturn JSON strictly matching this schema:\n{json.dumps(schema.model_json_schema())}"
            })

            response = await self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return schema.model_validate_json(content)
        except Exception as e:
            raise AIProviderError(f"OpenAI Structured Output error: {e}")


class OllamaProvider(BaseAIProvider):
    """Ollama Local LLM Provider implementation."""

    def __init__(self, config: Config):
        super().__init__(config)
        try:
            from openai import AsyncOpenAI
            base_url = f"{config.ollama_host.rstrip('/')}/v1"
            self.client = AsyncOpenAI(
                api_key="ollama",
                base_url=base_url,
            )
        except ImportError:
            raise AIProviderError("openai package is not installed.")

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.config.ollama_model,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise AIProviderError(f"Ollama API error ({self.config.ollama_host}): {e}")

    async def generate_structured(
        self, prompt: str, schema: Type[T], system_instruction: Optional[str] = None
    ) -> T:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({
                "role": "user",
                "content": f"{prompt}\nReturn JSON strictly matching schema:\n{json.dumps(schema.model_json_schema())}"
            })

            response = await self.client.chat.completions.create(
                model=self.config.ollama_model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return schema.model_validate_json(content)
        except Exception as e:
            raise AIProviderError(f"Ollama Structured Output error: {e}")


def get_ai_provider(config: Config) -> BaseAIProvider:
    """Factory to get selected AI provider."""
    provider = config.ai_provider.lower()
    if provider == "gemini":
        return GeminiProvider(config)
    elif provider == "openai":
        return OpenAIProvider(config)
    elif provider == "ollama":
        return OllamaProvider(config)
    else:
        raise AIProviderError(f"Unsupported AI provider: {provider}")
