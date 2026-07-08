#!/usr/bin/env python3
"""GetAiLab — Ollama LLM Provider (local, free)."""

import logging
import os
from typing import List, Optional

import requests

from llm.images import b64_encode, normalize_images

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama local inference provider."""

    supports_vision = True

    def __init__(self, endpoint: str = 'http://localhost:11434',
                 model: str = 'dolphin3:latest',
                 code_model: str = 'codellama:latest',
                 vision_model: str = 'llava:latest'):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.code_model = code_model
        self.vision_model = vision_model
        self.agent_name = os.getenv('AGENT_NAME', 'getailab')

    def _headers(self) -> dict:
        return {'X-Agent-Name': self.agent_name}

    def generate(self, prompt: str, system_prompt: str = '',
                 use_code_model: bool = False, timeout: Optional[int] = None,
                 images: Optional[List] = None) -> str:
        """Generate via Ollama. Uses /api/chat when images are provided."""
        if timeout is None:
            timeout = int(os.getenv("OLLAMA_TIMEOUT", "600"))
        if images:
            return self._generate_chat(prompt, system_prompt, self.vision_model, images, timeout)
        code_tokens = int(os.getenv("OLLAMA_NUM_PREDICT_CODE", "8192"))
        predict = code_tokens if use_code_model else None
        return self._generate_legacy(
            prompt, system_prompt,
            self.code_model if use_code_model else self.model,
            timeout,
            num_predict=predict,
        )

    def _generate_legacy(self, prompt: str, system_prompt: str, model: str, timeout: int,
                         num_predict: Optional[int] = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        if num_predict is None:
            num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
        resp = requests.post(
            f'{self.endpoint}/api/generate',
            json={
                'model': model,
                'prompt': full_prompt,
                'stream': False,
                'options': {'num_predict': num_predict},
            },
            headers=self._headers(),
            timeout=timeout,
        )
        if resp.status_code != 200:
            try:
                err = resp.json().get('error', resp.text)
            except Exception:
                err = resp.text or f'HTTP {resp.status_code}'
            return f"ERROR: Ollama ({model}): {err}"
        return resp.json().get('response', '')

    def _generate_chat(self, prompt: str, system_prompt: str, model: str,
                       images: List, timeout: int) -> str:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({
            'role': 'user',
            'content': prompt,
            'images': [b64_encode(b) for b in normalize_images(images)],
        })
        resp = requests.post(
            f'{self.endpoint}/api/chat',
            json={'model': model, 'messages': messages, 'stream': False},
            headers=self._headers(),
            timeout=timeout,
        )
        if resp.status_code != 200:
            try:
                err = resp.json().get('error', resp.text)
            except Exception:
                err = resp.text or f'HTTP {resp.status_code}'
            return f"ERROR: Ollama ({model}): {err}"
        data = resp.json()
        return data.get('message', {}).get('content', '')

    def is_ready(self) -> bool:
        try:
            resp = requests.get(f'{self.endpoint}/api/tags', timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama not ready: {e}")
            return False

    def get_info(self) -> dict:
        return {
            'provider': 'ollama',
            'endpoint': self.endpoint,
            'model': self.model,
            'code_model': self.code_model,
            'vision_model': self.vision_model,
        }