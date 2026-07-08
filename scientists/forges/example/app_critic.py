#!/usr/bin/env python3
"""Forged scientist: critic · lab example"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "scientists")]

os.environ.setdefault("LAB_ID", "example")
os.environ.setdefault("PERSONAS_YAML", "personas/example_squad.yaml")

from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config("critic", overrides={"port": 5126})
app = create_agent_app(AGENT_CONFIG)

if __name__ == "__main__":
    run_agent(app, AGENT_CONFIG)