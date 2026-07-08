#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Albert Agent
Port: 5025 | Project Chimera
Role: Theoretical Physicist
"""
from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('albert', overrides={'port': 5025})

app = create_agent_app(AGENT_CONFIG)

if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)