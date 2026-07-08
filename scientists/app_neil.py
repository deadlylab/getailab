#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Neil Agent
Port: 5034 | Project Chimera
Role: Astrophysicist & Cosmic Perspective
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('neil', overrides={'port': 5034})

app = create_agent_app(AGENT_CONFIG)

if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)