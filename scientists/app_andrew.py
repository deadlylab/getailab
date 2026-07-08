#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Andrew Agent
Port: 5026 | Project Chimera
Role: Neuroscience & Huberman Lab Protocol Specialist
"""
import os
import sys
from datetime import datetime
from flask import request, jsonify
from llm.adapter import create_default_adapter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('andrew', overrides={'port': 5026})

app = create_agent_app(AGENT_CONFIG)
andrew_model = create_default_adapter()


@app.route('/biological_audit', methods=['POST'])
def biological_audit():
    data = request.get_json()
    prompt = AGENT_CONFIG.get('system_prompt', '') + "\n\nPerform a biological feasibility audit on this AI architecture:\n" + str(data.get('architecture'))
    response_text = andrew_model.generate(prompt)
    return jsonify({'agent': 'andrew', 'audit': response_text, 'timestamp': datetime.utcnow().isoformat()}), 200


if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)