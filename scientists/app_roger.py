#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Roger Agent
Port: 5038 | Project Chimera
Role: Mathematical Physicist & Consciousness Theorist
"""
from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('roger', overrides={'port': 5038})

app = create_agent_app(AGENT_CONFIG)

if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)