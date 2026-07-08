#!/usr/bin/env python3
"""GetAiLab — Google Gemini LLM Provider (optional cloud backend)."""

import logging
from typing import List, Optional

import requests

from llm.images import b64_encode, guess_media_type, normalize_images

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Google Gemini API provider."""

    supports_vision = True
    API_URL = 'https://generativelanguage.googleapis.com/v1beta/models'

    def __init__(self, api_key: str,
                 model: str = 'gemini-2.0-flash',
                 code_model: str = 'gemini-2.0-flash',
                 vision_model: str = 'gemini-2.0-flash'):
        self.api_key = api_key
        self.model = model
        self.code_model = code_model
        self.vision_model = vision_model

    def generate(self, prompt: str, system_prompt: str = '',
                 use_code_model: bool = False, timeout: int = 300,
                 images: Optional[List] = None) -> str:
        """Generate text via Gemini API."""
        if images:
            model = self.vision_model
        else:
            model = self.code_model if use_code_model else self.model

        parts = []
        if system_prompt:
            parts.append({'text': system_prompt})
        for raw in normalize_images(images or []):
            parts.append({
                'inline_data': {
                    'mime_type': guess_media_type(raw),
                    'data': b64_encode(raw),
                }
            })
        parts.append({'text': prompt})

        resp = requests.post(
            f'{self.API_URL}/{model}:generateContent',
            params={'key': self.api_key},
            json={
                'contents': [{'parts': parts}],
                'generationConfig': {'maxOutputTokens': 4096},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Unexpected Gemini response structure: {e}")
            return ''

    def is_ready(self) -> bool:
        return bool(self.api_key)

    def get_info(self) -> dict:
        return {
            'provider': 'google',
            'model': self.model,
            'code_model': self.code_model,
            'vision_model': self.vision_model,
        }