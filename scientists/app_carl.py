#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Carl Agent
Port: 5028 | Project Chimera
Role: Analytical Psychology & Archetypal Analysis
"""
import os
import sys
from datetime import datetime
from flask import request, jsonify
from llm.adapter import create_default_adapter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config('carl', overrides={'port': 5028})

app = create_agent_app(AGENT_CONFIG)
jung_model = create_default_adapter()


@app.route('/analyze_symbol', methods=['POST'])
def analyze_symbol():
    data = request.get_json()
    prompt = AGENT_CONFIG['system_prompt'] + "\n\nAnalyze the symbolic and archetypal weight of this AI output:\n" + str(data.get('output'))
    response_text = jung_model.generate(prompt)
    return jsonify({'agent': 'carl', 'analysis': response_text, 'timestamp': datetime.utcnow().isoformat()}), 200


if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)