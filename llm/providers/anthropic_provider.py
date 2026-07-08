#!/usr/bin/env python3
"""GetAiLab — Anthropic Claude LLM Provider."""

import logging
from typing import List, Optional

import requests

from llm.images import b64_encode, guess_media_type, normalize_images

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude API provider."""

    supports_vision = True
    API_URL = 'https://api.anthropic.com/v1/messages'

    def __init__(self, api_key: str,
                 model: str = 'claude-sonnet-4-20250514',
                 code_model: str = 'claude-sonnet-4-20250514',
                 vision_model: str = 'claude-sonnet-4-20250514'):
        self.api_key = api_key
        self.model = model
        self.code_model = code_model
        self.vision_model = vision_model

    def _headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
        }

    def generate(self, prompt: str, system_prompt: str = '',
                 use_code_model: bool = False, timeout: int = 300,
                 images: Optional[List] = None) -> str:
        """Generate text via Anthropic Messages API."""
        if images:
            model = self.vision_model
        else:
            model = self.code_model if use_code_model else self.model

        content = []
        for raw in normalize_images(images or []):
            content.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': guess_media_type(raw),
                    'data': b64_encode(raw),
                },
            })
        content.append({'type': 'text', 'text': prompt})

        body = {
            'model': model,
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': content}],
        }
        if system_prompt:
            body['system'] = system_prompt

        resp = requests.post(
            self.API_URL,
            headers=self._headers(),
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data['content'][0]['text']
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Unexpected Anthropic response structure: {e}")
            return ''

    def is_ready(self) -> bool:
        return bool(self.api_key)

    def get_info(self) -> dict:
        return {
            'provider': 'anthropic',
            'model': self.model,
            'code_model': self.code_model,
            'vision_model': self.vision_model,
        }