#!/usr/bin/env python3
"""
GetAiLab — Multi-Provider LLM Adapter
Unified interface for 20+ LLM providers. Factory dispatches to the right backend.
"""

import os
from typing import Optional
from llm.providers.ollama import OllamaProvider
from llm.providers.openai_compat import OpenAICompatProvider


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER CATALOG — every provider the user can pick from
# ══════════════════════════════════════════════════════════════════════════════

PROVIDER_CATALOG = {
    # ── Local / Self-Hosted ──────────────────────────────────────────────────
    "ollama": {
        "name": "Ollama",
        "category": "local",
        "description": "Run open-source models locally — free, private, no API key needed",
        "endpoint": "http://localhost:11434",
        "api_key_env": "",
        "backend": "ollama",
        "models": [
            {"id": "dolphin3:latest",         "name": "Dolphin 3",            "params": "8B",   "type": "chat"},
            {"id": "llama3.3:latest",          "name": "Llama 3.3",            "params": "70B",  "type": "chat"},
            {"id": "llama3.2:latest",          "name": "Llama 3.2",            "params": "3B",   "type": "chat"},
            {"id": "llama3.1:latest",          "name": "Llama 3.1",            "params": "8B",   "type": "chat"},
            {"id": "mistral:latest",           "name": "Mistral 7B",           "params": "7B",   "type": "chat"},
            {"id": "mixtral:latest",           "name": "Mixtral 8x7B",         "params": "47B",  "type": "chat"},
            {"id": "gemma2:latest",            "name": "Gemma 2",              "params": "9B",   "type": "chat"},
            {"id": "gemma3:latest",            "name": "Gemma 3",              "params": "12B",  "type": "chat"},
            {"id": "phi4:latest",              "name": "Phi-4",                "params": "14B",  "type": "chat"},
            {"id": "qwen2.5:latest",           "name": "Qwen 2.5",            "params": "7B",   "type": "chat"},
            {"id": "qwen3:latest",             "name": "Qwen 3",              "params": "8B",   "type": "chat"},
            {"id": "deepseek-r1:latest",       "name": "DeepSeek R1",          "params": "7B",   "type": "reasoning"},
            {"id": "command-r:latest",         "name": "Command R",            "params": "35B",  "type": "chat"},
            {"id": "codellama:latest",         "name": "Code Llama",           "params": "7B",   "type": "code"},
            {"id": "starcoder2:latest",        "name": "StarCoder 2",          "params": "7B",   "type": "code"},
            {"id": "deepseek-coder-v2:latest", "name": "DeepSeek Coder V2",   "params": "16B",  "type": "code"},
            {"id": "qwen2.5-coder:latest",     "name": "Qwen 2.5 Coder",      "params": "7B",   "type": "code"},
            {"id": "nomic-embed-text:latest",  "name": "Nomic Embed",          "params": "137M", "type": "embedding"},
        ],
        "default_model": "dolphin3:latest",
        "default_code_model": "codellama:latest",
    },
    "lmstudio": {
        "name": "LM Studio",
        "category": "local",
        "description": "Desktop app for local models — OpenAI-compatible API",
        "endpoint": "http://localhost:1234/v1",
        "api_key_env": "",
        "backend": "openai_compat",
        "models": [
            {"id": "local-model", "name": "Currently loaded model", "params": "varies", "type": "chat"},
        ],
        "default_model": "local-model",
        "default_code_model": "local-model",
    },
    "llamacpp": {
        "name": "llama.cpp Server",
        "category": "local",
        "description": "llama.cpp HTTP server — lightweight, fast inference",
        "endpoint": "http://localhost:8080/v1",
        "api_key_env": "",
        "backend": "openai_compat",
        "models": [
            {"id": "local-model", "name": "Currently loaded model", "params": "varies", "type": "chat"},
        ],
        "default_model": "local-model",
        "default_code_model": "local-model",
    },
    "jan": {
        "name": "Jan",
        "category": "local",
        "description": "Open-source ChatGPT alternative with local models",
        "endpoint": "http://localhost:1337/v1",
        "api_key_env": "",
        "backend": "openai_compat",
        "models": [
            {"id": "local-model", "name": "Currently loaded model", "params": "varies", "type": "chat"},
        ],
        "default_model": "local-model",
        "default_code_model": "local-model",
    },

    # ── OpenAI ───────────────────────────────────────────────────────────────
    "openai": {
        "name": "OpenAI",
        "category": "cloud",
        "description": "GPT-4o, o1, o3 — the OG",
        "endpoint": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "gpt-4o",            "name": "GPT-4o",           "params": "",   "type": "chat"},
            {"id": "gpt-4o-mini",        "name": "GPT-4o Mini",      "params": "",   "type": "chat"},
            {"id": "gpt-4-turbo",        "name": "GPT-4 Turbo",      "params": "",   "type": "chat"},
            {"id": "o1",                 "name": "o1",               "params": "",   "type": "reasoning"},
            {"id": "o1-mini",            "name": "o1 Mini",          "params": "",   "type": "reasoning"},
            {"id": "o3",                 "name": "o3",               "params": "",   "type": "reasoning"},
            {"id": "o3-mini",            "name": "o3 Mini",          "params": "",   "type": "reasoning"},
            {"id": "o4-mini",            "name": "o4 Mini",          "params": "",   "type": "reasoning"},
            {"id": "gpt-4.1",           "name": "GPT-4.1",          "params": "",   "type": "chat"},
            {"id": "gpt-4.1-mini",      "name": "GPT-4.1 Mini",     "params": "",   "type": "chat"},
            {"id": "gpt-4.1-nano",      "name": "GPT-4.1 Nano",     "params": "",   "type": "chat"},
        ],
        "default_model": "gpt-4o",
        "default_code_model": "gpt-4o",
    },

    # ── Anthropic ────────────────────────────────────────────────────────────
    "anthropic": {
        "name": "Anthropic",
        "category": "cloud",
        "description": "Claude — Opus, Sonnet, Haiku",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "api_key_env": "ANTHROPIC_API_KEY",
        "backend": "anthropic",
        "models": [
            {"id": "claude-opus-4-20250514",     "name": "Claude Opus 4",       "params": "",  "type": "reasoning"},
            {"id": "claude-sonnet-4-20250514",   "name": "Claude Sonnet 4",     "params": "",  "type": "chat"},
            {"id": "claude-haiku-4-5-20251001",  "name": "Claude Haiku 4.5",    "params": "",  "type": "chat"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet",   "params": "",  "type": "chat"},
            {"id": "claude-3-5-haiku-20241022",  "name": "Claude 3.5 Haiku",    "params": "",  "type": "chat"},
        ],
        "default_model": "claude-sonnet-4-20250514",
        "default_code_model": "claude-sonnet-4-20250514",
    },

    # ── Google ───────────────────────────────────────────────────────────────
    "google": {
        "name": "Google Gemini",
        "category": "cloud",
        "description": "Gemini 2.5 Pro, Flash, and more",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
        "api_key_env": "GOOGLE_API_KEY",
        "backend": "google",
        "models": [
            {"id": "gemini-2.5-pro",    "name": "Gemini 2.5 Pro",      "params": "",  "type": "reasoning"},
            {"id": "gemini-2.5-flash",   "name": "Gemini 2.5 Flash",    "params": "",  "type": "chat"},
            {"id": "gemini-2.0-flash",   "name": "Gemini 2.0 Flash",    "params": "",  "type": "chat"},
            {"id": "gemini-1.5-pro",     "name": "Gemini 1.5 Pro",      "params": "",  "type": "chat"},
            {"id": "gemini-1.5-flash",   "name": "Gemini 1.5 Flash",    "params": "",  "type": "chat"},
        ],
        "default_model": "gemini-2.5-flash",
        "default_code_model": "gemini-2.5-flash",
    },

    # ── Groq ─────────────────────────────────────────────────────────────────
    "groq": {
        "name": "Groq",
        "category": "cloud",
        "description": "Blazing fast inference — LPU hardware, free tier available",
        "endpoint": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "llama-3.3-70b-versatile",  "name": "Llama 3.3 70B",       "params": "70B",  "type": "chat"},
            {"id": "llama-3.1-8b-instant",      "name": "Llama 3.1 8B",        "params": "8B",   "type": "chat"},
            {"id": "llama-3.2-90b-vision-preview","name": "Llama 3.2 90B Vision","params": "90B",  "type": "vision"},
            {"id": "mixtral-8x7b-32768",        "name": "Mixtral 8x7B",        "params": "47B",  "type": "chat"},
            {"id": "gemma2-9b-it",              "name": "Gemma 2 9B",          "params": "9B",   "type": "chat"},
            {"id": "qwen-qwq-32b",             "name": "Qwen QWQ 32B",        "params": "32B",  "type": "reasoning"},
            {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 70B", "params": "70B",  "type": "reasoning"},
        ],
        "default_model": "llama-3.3-70b-versatile",
        "default_code_model": "llama-3.3-70b-versatile",
    },

    # ── Together AI ──────────────────────────────────────────────────────────
    "together": {
        "name": "Together AI",
        "category": "cloud",
        "description": "100+ open-source models — fast, cheap inference",
        "endpoint": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",     "name": "Llama 3.3 70B Turbo",    "params": "70B",  "type": "chat"},
            {"id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo","name": "Llama 3.1 405B Turbo",   "params": "405B", "type": "chat"},
            {"id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "name": "Llama 3.1 8B Turbo",     "params": "8B",   "type": "chat"},
            {"id": "mistralai/Mixtral-8x22B-Instruct-v0.1",       "name": "Mixtral 8x22B",          "params": "141B", "type": "chat"},
            {"id": "mistralai/Mistral-7B-Instruct-v0.3",          "name": "Mistral 7B v0.3",        "params": "7B",   "type": "chat"},
            {"id": "Qwen/Qwen2.5-72B-Instruct-Turbo",             "name": "Qwen 2.5 72B Turbo",     "params": "72B",  "type": "chat"},
            {"id": "deepseek-ai/DeepSeek-R1",                     "name": "DeepSeek R1",            "params": "671B", "type": "reasoning"},
            {"id": "deepseek-ai/DeepSeek-V3",                     "name": "DeepSeek V3",            "params": "685B", "type": "chat"},
            {"id": "google/gemma-2-27b-it",                        "name": "Gemma 2 27B",            "params": "27B",  "type": "chat"},
            {"id": "Qwen/Qwen2.5-Coder-32B-Instruct",             "name": "Qwen 2.5 Coder 32B",    "params": "32B",  "type": "code"},
        ],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "default_code_model": "Qwen/Qwen2.5-Coder-32B-Instruct",
    },

    # ── Fireworks AI ─────────────────────────────────────────────────────────
    "fireworks": {
        "name": "Fireworks AI",
        "category": "cloud",
        "description": "Fast inference for open-source models — great for production",
        "endpoint": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "accounts/fireworks/models/llama-v3p3-70b-instruct",   "name": "Llama 3.3 70B",     "params": "70B",  "type": "chat"},
            {"id": "accounts/fireworks/models/llama-v3p1-405b-instruct",  "name": "Llama 3.1 405B",    "params": "405B", "type": "chat"},
            {"id": "accounts/fireworks/models/llama-v3p1-8b-instruct",    "name": "Llama 3.1 8B",      "params": "8B",   "type": "chat"},
            {"id": "accounts/fireworks/models/mixtral-8x22b-instruct",    "name": "Mixtral 8x22B",     "params": "141B", "type": "chat"},
            {"id": "accounts/fireworks/models/qwen2p5-72b-instruct",      "name": "Qwen 2.5 72B",      "params": "72B",  "type": "chat"},
            {"id": "accounts/fireworks/models/deepseek-r1",               "name": "DeepSeek R1",       "params": "671B", "type": "reasoning"},
            {"id": "accounts/fireworks/models/deepseek-v3",               "name": "DeepSeek V3",       "params": "685B", "type": "chat"},
        ],
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "default_code_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    },

    # ── DeepSeek ─────────────────────────────────────────────────────────────
    "deepseek": {
        "name": "DeepSeek",
        "category": "cloud",
        "description": "DeepSeek API — R1 reasoning + V3 chat, dirt cheap",
        "endpoint": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "deepseek-chat",      "name": "DeepSeek V3 (Chat)",     "params": "685B", "type": "chat"},
            {"id": "deepseek-reasoner",   "name": "DeepSeek R1 (Reasoner)", "params": "671B", "type": "reasoning"},
            {"id": "deepseek-coder",      "name": "DeepSeek Coder",         "params": "",     "type": "code"},
        ],
        "default_model": "deepseek-chat",
        "default_code_model": "deepseek-coder",
    },

    # ── Mistral AI ───────────────────────────────────────────────────────────
    "mistral": {
        "name": "Mistral AI",
        "category": "cloud",
        "description": "French AI lab — Mistral Large, Codestral, open models",
        "endpoint": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "mistral-large-latest",    "name": "Mistral Large",       "params": "",    "type": "chat"},
            {"id": "mistral-medium-latest",   "name": "Mistral Medium",      "params": "",    "type": "chat"},
            {"id": "mistral-small-latest",    "name": "Mistral Small",       "params": "",    "type": "chat"},
            {"id": "open-mistral-nemo",       "name": "Mistral Nemo",        "params": "12B", "type": "chat"},
            {"id": "codestral-latest",        "name": "Codestral",           "params": "",    "type": "code"},
            {"id": "open-mixtral-8x22b",      "name": "Mixtral 8x22B",       "params": "141B","type": "chat"},
            {"id": "pixtral-large-latest",    "name": "Pixtral Large",       "params": "",    "type": "vision"},
        ],
        "default_model": "mistral-large-latest",
        "default_code_model": "codestral-latest",
    },

    # ── Cohere ───────────────────────────────────────────────────────────────
    "cohere": {
        "name": "Cohere",
        "category": "cloud",
        "description": "Command R+ — enterprise-grade RAG and search",
        "endpoint": "https://api.cohere.com/v2",
        "api_key_env": "COHERE_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "command-r-plus",     "name": "Command R+",          "params": "104B", "type": "chat"},
            {"id": "command-r",          "name": "Command R",           "params": "35B",  "type": "chat"},
            {"id": "command-light",      "name": "Command Light",       "params": "",     "type": "chat"},
        ],
        "default_model": "command-r-plus",
        "default_code_model": "command-r-plus",
    },

    # ── Perplexity ───────────────────────────────────────────────────────────
    "perplexity": {
        "name": "Perplexity",
        "category": "cloud",
        "description": "AI search engine — models with live internet access",
        "endpoint": "https://api.perplexity.ai",
        "api_key_env": "PERPLEXITY_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "sonar-pro",          "name": "Sonar Pro",         "params": "",  "type": "search"},
            {"id": "sonar",              "name": "Sonar",             "params": "",  "type": "search"},
            {"id": "sonar-reasoning-pro","name": "Sonar Reasoning Pro","params": "", "type": "reasoning"},
            {"id": "sonar-reasoning",    "name": "Sonar Reasoning",   "params": "",  "type": "reasoning"},
        ],
        "default_model": "sonar-pro",
        "default_code_model": "sonar-pro",
    },

    # ── OpenRouter ───────────────────────────────────────────────────────────
    "openrouter": {
        "name": "OpenRouter",
        "category": "cloud",
        "description": "One API key, 200+ models from every provider — model marketplace",
        "endpoint": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "anthropic/claude-sonnet-4",    "name": "Claude Sonnet 4",       "params": "",    "type": "chat"},
            {"id": "anthropic/claude-haiku-4",     "name": "Claude Haiku 4",        "params": "",    "type": "chat"},
            {"id": "openai/gpt-4o",                "name": "GPT-4o",               "params": "",    "type": "chat"},
            {"id": "openai/o3-mini",               "name": "o3 Mini",              "params": "",    "type": "reasoning"},
            {"id": "google/gemini-2.5-flash",      "name": "Gemini 2.5 Flash",      "params": "",    "type": "chat"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B",   "params": "70B", "type": "chat"},
            {"id": "deepseek/deepseek-r1",         "name": "DeepSeek R1",          "params": "671B","type": "reasoning"},
            {"id": "deepseek/deepseek-chat",       "name": "DeepSeek V3",          "params": "685B","type": "chat"},
            {"id": "mistralai/mistral-large",      "name": "Mistral Large",        "params": "",    "type": "chat"},
            {"id": "qwen/qwen-2.5-72b-instruct",  "name": "Qwen 2.5 72B",         "params": "72B", "type": "chat"},
        ],
        "default_model": "anthropic/claude-sonnet-4",
        "default_code_model": "anthropic/claude-sonnet-4",
    },

    # ── xAI (Grok) ──────────────────────────────────────────────────────────
    "xai": {
        "name": "xAI (Grok)",
        "category": "cloud",
        "description": "Grok models from Elon's xAI",
        "endpoint": "https://api.x.ai/v1",
        "api_key_env": "XAI_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "grok-3",          "name": "Grok 3",          "params": "", "type": "chat"},
            {"id": "grok-3-mini",     "name": "Grok 3 Mini",     "params": "", "type": "chat"},
            {"id": "grok-2",          "name": "Grok 2",          "params": "", "type": "chat"},
        ],
        "default_model": "grok-3",
        "default_code_model": "grok-3",
    },

    # ── Cerebras ─────────────────────────────────────────────────────────────
    "cerebras": {
        "name": "Cerebras",
        "category": "cloud",
        "description": "Fastest inference on the planet — wafer-scale chips",
        "endpoint": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "llama-3.3-70b",    "name": "Llama 3.3 70B",   "params": "70B", "type": "chat"},
            {"id": "llama-3.1-8b",     "name": "Llama 3.1 8B",    "params": "8B",  "type": "chat"},
            {"id": "qwen-2.5-32b",     "name": "Qwen 2.5 32B",    "params": "32B", "type": "chat"},
            {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 70B", "params": "70B", "type": "reasoning"},
        ],
        "default_model": "llama-3.3-70b",
        "default_code_model": "llama-3.3-70b",
    },

    # ── SambaNova ────────────────────────────────────────────────────────────
    "sambanova": {
        "name": "SambaNova",
        "category": "cloud",
        "description": "Custom AI chips — fast open-source model inference, free tier",
        "endpoint": "https://api.sambanova.ai/v1",
        "api_key_env": "SAMBANOVA_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "Meta-Llama-3.3-70B-Instruct",  "name": "Llama 3.3 70B",   "params": "70B",  "type": "chat"},
            {"id": "Meta-Llama-3.1-405B-Instruct",  "name": "Llama 3.1 405B",  "params": "405B", "type": "chat"},
            {"id": "Meta-Llama-3.1-8B-Instruct",    "name": "Llama 3.1 8B",    "params": "8B",   "type": "chat"},
            {"id": "DeepSeek-R1",                    "name": "DeepSeek R1",     "params": "671B", "type": "reasoning"},
            {"id": "Qwen2.5-72B-Instruct",           "name": "Qwen 2.5 72B",    "params": "72B",  "type": "chat"},
            {"id": "Qwen2.5-Coder-32B-Instruct",     "name": "Qwen 2.5 Coder",  "params": "32B",  "type": "code"},
        ],
        "default_model": "Meta-Llama-3.3-70B-Instruct",
        "default_code_model": "Qwen2.5-Coder-32B-Instruct",
    },

    # ── Lepton AI ────────────────────────────────────────────────────────────
    "lepton": {
        "name": "Lepton AI",
        "category": "cloud",
        "description": "Serverless AI — pay-per-token, fast inference",
        "endpoint": "https://llama3-3-70b.lepton.run/api/v1",
        "api_key_env": "LEPTON_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "llama3-3-70b",    "name": "Llama 3.3 70B",    "params": "70B", "type": "chat"},
            {"id": "mixtral-8x7b",     "name": "Mixtral 8x7B",     "params": "47B", "type": "chat"},
        ],
        "default_model": "llama3-3-70b",
        "default_code_model": "llama3-3-70b",
    },

    # ── Novita AI ────────────────────────────────────────────────────────────
    "novita": {
        "name": "Novita AI",
        "category": "cloud",
        "description": "Cheap open-source model hosting — good for bulk inference",
        "endpoint": "https://api.novita.ai/v3/openai",
        "api_key_env": "NOVITA_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "meta-llama/llama-3.3-70b-instruct",  "name": "Llama 3.3 70B",   "params": "70B",  "type": "chat"},
            {"id": "deepseek/deepseek-r1",                "name": "DeepSeek R1",     "params": "671B", "type": "reasoning"},
            {"id": "mistralai/mistral-large-latest",      "name": "Mistral Large",   "params": "",     "type": "chat"},
        ],
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "default_code_model": "meta-llama/llama-3.3-70b-instruct",
    },

    # ── AI21 Labs ────────────────────────────────────────────────────────────
    "ai21": {
        "name": "AI21 Labs",
        "category": "cloud",
        "description": "Jamba — Mamba-based hybrid architecture, long context",
        "endpoint": "https://api.ai21.com/studio/v1",
        "api_key_env": "AI21_API_KEY",
        "backend": "openai_compat",
        "models": [
            {"id": "jamba-1.5-large",  "name": "Jamba 1.5 Large",  "params": "398B", "type": "chat"},
            {"id": "jamba-1.5-mini",   "name": "Jamba 1.5 Mini",   "params": "52B",  "type": "chat"},
        ],
        "default_model": "jamba-1.5-large",
        "default_code_model": "jamba-1.5-large",
    },

    # ── Custom / Self-hosted ─────────────────────────────────────────────────
    "custom": {
        "name": "Custom (OpenAI-compatible)",
        "category": "custom",
        "description": "Any OpenAI-compatible API — vLLM, TGI, Aphrodite, etc.",
        "endpoint": "",
        "api_key_env": "CUSTOM_API_KEY",
        "backend": "openai_compat",
        "models": [],
        "default_model": "",
        "default_code_model": "",
    },
}


def get_provider_catalog() -> dict:
    """Return the full provider catalog for UIs to display."""
    return PROVIDER_CATALOG


def get_api_key_env(provider: str) -> str:
    """Return the env var name for a provider's API key."""
    entry = PROVIDER_CATALOG.get(provider, {})
    return entry.get("api_key_env", "")


def _ollama_reachable(endpoint: str = "http://localhost:11434") -> bool:
    try:
        import requests
        resp = requests.get(f"{endpoint.rstrip('/')}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def _detect_cloud_provider(prefix: str = "") -> str:
    """Pick first cloud provider with an API key when LLM_PROVIDER=auto."""
    for name in (
        "openai", "anthropic", "google", "groq", "together", "fireworks",
        "deepseek", "mistral", "cohere", "perplexity", "openrouter",
    ):
        key_env = get_api_key_env(name)
        if key_env and os.getenv(f"{prefix}{key_env}", "").strip():
            return name
    return "ollama"


def get_env_provider_config(prefix: str = "") -> dict:
    """Build provider config from environment variables.

    Resolution order:
      1. LLM_PROVIDER if set (use google, openai, ollama, auto, etc.)
      2. Default: ollama (local-first — matches self-host design)
      3. LLM_PROVIDER=auto → Ollama if reachable, else first cloud key found

    API keys never override an explicit LLM_PROVIDER. Set LLM_PROVIDER=google
    (or openai, etc.) to use a cloud backend; leave unset for local Ollama.
    """
    provider = os.getenv(f"{prefix}LLM_PROVIDER", "").strip().lower()
    if provider == "auto":
        endpoint = os.getenv(f"{prefix}LLM_ENDPOINT", "").strip() or "http://localhost:11434"
        provider = "ollama" if _ollama_reachable(endpoint) else _detect_cloud_provider(prefix)
    if not provider:
        provider = "ollama"

    model = os.getenv(f"{prefix}LLM_MODEL", "").strip()
    code_model = os.getenv(f"{prefix}LLM_MODEL_CODE", "").strip()
    vision_model = os.getenv(f"{prefix}LLM_MODEL_VISION", "").strip()
    endpoint = os.getenv(f"{prefix}LLM_ENDPOINT", "").strip()
    api_key = os.getenv(f"{prefix}LLM_API_KEY", "").strip()

    if not api_key:
        api_key_env = get_api_key_env(provider)
        if api_key_env:
            api_key = os.getenv(f"{prefix}{api_key_env}", "").strip()

    return {
        "provider": provider,
        "model": model,
        "code_model": code_model,
        "vision_model": vision_model,
        "endpoint": endpoint,
        "api_key": api_key,
    }


def create_default_adapter(prefix: str = "") -> 'LLMAdapter':
    """Create an LLMAdapter from environment variables with fallback defaults."""
    return LLMAdapter(get_env_provider_config(prefix))


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def create_provider(config: dict):
    """Factory: create the right LLM provider from config."""
    provider = config.get('provider', 'ollama').lower()
    model = config.get('model', '')
    code_model = config.get('code_model', '')
    vision_model = config.get('vision_model', '')
    endpoint = config.get('endpoint', '')
    api_key = config.get('api_key', '')

    # Look up in catalog for defaults
    catalog_entry = PROVIDER_CATALOG.get(provider, {})
    backend = catalog_entry.get('backend', provider)

    if backend == 'ollama' or provider == 'ollama':
        return OllamaProvider(
            endpoint=endpoint or catalog_entry.get('endpoint', 'http://localhost:11434'),
            model=model or catalog_entry.get('default_model', 'dolphin3:latest'),
            code_model=code_model or catalog_entry.get('default_code_model', 'codellama:latest'),
            vision_model=vision_model or 'llava:latest',
        )

    elif backend == 'openai_compat':
        default = model or catalog_entry.get('default_model', 'gpt-4o')
        return OpenAICompatProvider(
            endpoint=endpoint or catalog_entry.get('endpoint', 'https://api.openai.com/v1'),
            api_key=api_key,
            model=default,
            code_model=code_model or catalog_entry.get('default_code_model', 'gpt-4o'),
            vision_model=vision_model or default,
        )

    elif backend == 'anthropic' or provider == 'anthropic':
        from llm.providers.anthropic_provider import AnthropicProvider
        default = model or catalog_entry.get('default_model', 'claude-sonnet-4-20250514')
        return AnthropicProvider(
            api_key=api_key,
            model=default,
            code_model=code_model or catalog_entry.get('default_code_model', 'claude-sonnet-4-20250514'),
            vision_model=vision_model or default,
        )

    elif backend == 'google' or provider == 'google':
        from llm.providers.google_provider import GoogleProvider
        default = model or catalog_entry.get('default_model', 'gemini-2.0-flash')
        return GoogleProvider(
            api_key=api_key,
            model=default,
            code_model=code_model or catalog_entry.get('default_code_model', 'gemini-2.0-flash'),
            vision_model=vision_model or default,
        )

    else:
        # Fallback: treat unknown providers as OpenAI-compatible
        if endpoint:
            return OpenAICompatProvider(
                endpoint=endpoint,
                api_key=api_key,
                model=model or 'gpt-4o',
                code_model=code_model or 'gpt-4o',
                vision_model=vision_model or model or 'gpt-4o',
            )
        raise ValueError(f"Unknown LLM provider: {provider}")


def _default_generate_timeout() -> int:
    """Seconds to wait for an LLM reply (Ollama on local hardware is slow)."""
    raw = os.getenv("OLLAMA_TIMEOUT") or os.getenv("LLM_TIMEOUT")
    if raw:
        return int(raw)
    return 600


class LLMAdapter:
    """Unified LLM interface used by all GetAiLab components."""

    def __init__(self, config: dict):
        self.config = config
        self.provider = create_provider(config)
        self.agent_name = os.getenv('AGENT_NAME', 'getailab')

    def generate(self, prompt: str, system_prompt: str = '',
                 use_code_model: bool = False, timeout: Optional[int] = None,
                 images=None) -> str:
        """Generate text. Pass images=[bytes|path] for vision when supported."""
        if timeout is None:
            timeout = _default_generate_timeout()
        return self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            use_code_model=use_code_model,
            timeout=timeout,
            images=images,
        )

    def supports_vision(self) -> bool:
        """Whether the active provider can accept image inputs."""
        return bool(getattr(self.provider, 'supports_vision', False))

    def is_ready(self) -> bool:
        """Check if the LLM backend is responsive."""
        return self.provider.is_ready()

    def get_info(self) -> dict:
        """Get provider info for health checks."""
        info = self.provider.get_info()
        info['supports_vision'] = self.supports_vision()
        info['configured_provider'] = self.config.get('provider', 'ollama')
        return info
