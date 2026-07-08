#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Alan Agent
Port: 5027 | Project Chimera
Role: Philosopher of Mind & Epistemology
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('alan', overrides={'port': 5027})

app = create_agent_app(AGENT_CONFIG)

if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)