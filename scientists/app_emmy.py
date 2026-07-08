#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Emmy Agent
Port: 5029 | Project Chimera
Role: Mathematician — Symmetry & Formal Methods
"""
import os
import sys
from datetime import datetime
from flask import request, jsonify
from llm.adapter import create_default_adapter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('emmy', overrides={'port': 5029})

app = create_agent_app(AGENT_CONFIG)
emmy_model = create_default_adapter()


@app.route('/formalize', methods=['POST'])
def formalize():
    data = request.get_json()
    prompt = "Formalize this concept mathematically:\nConcept: " + str(data.get('concept'))
    response_text = emmy_model.generate(prompt)
    return jsonify({'agent': 'emmy', 'formalization': response_text, 'timestamp': datetime.utcnow().isoformat()}), 200


if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)