#!/usr/bin/env python3
"""GetAiLab — OpenAI-Compatible LLM Provider.
Works with OpenAI, Groq, Together, Fireworks, LM Studio, and any OpenAI-compatible API.
"""

import logging
from typing import List, Optional

import requests

from llm.images import b64_encode, guess_media_type, normalize_images

logger = logging.getLogger(__name__)


class OpenAICompatProvider:
    """OpenAI-compatible API provider."""

    supports_vision = True

    def __init__(self, endpoint: str, api_key: str,
                 model: str = 'gpt-4o', code_model: str = 'gpt-4o',
                 vision_model: str = 'gpt-4o'):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.code_model = code_model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        h = {'Content-Type': 'application/json'}
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
        return h

    def generate(self, prompt: str, system_prompt: str = '',
                 use_code_model: bool = False, timeout: int = 300,
                 images: Optional[List] = None) -> str:
        """Generate text via OpenAI-compatible /chat/completions."""
        model = self.vision_model if images else (self.code_model if use_code_model else self.model)

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})

        if images:
            content = [{'type': 'text', 'text': prompt}]
            for raw in normalize_images(images):
                media = guess_media_type(raw)
                content.append({
                    'type': 'image_url',
                    'image_url': {'url': f'data:{media};base64,{b64_encode(raw)}'},
                })
            messages.append({'role': 'user', 'content': content})
        else:
            messages.append({'role': 'user', 'content': prompt})

        resp = requests.post(
            f'{self.endpoint}/chat/completions',
            headers=self._headers(),
            json={
                'model': model,
                'messages': messages,
                'max_tokens': 4096,
                'stream': False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Unexpected OpenAI-compatible response structure: {e}")
            return ''

    def is_ready(self) -> bool:
        try:
            resp = requests.get(
                f'{self.endpoint}/models',
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"OpenAI-compatible provider not ready: {e}")
            return False

    def get_info(self) -> dict:
        return {
            'provider': 'openai_compatible',
            'endpoint': self.endpoint,
            'model': self.model,
            'code_model': self.code_model,
            'vision_model': self.vision_model,
        }