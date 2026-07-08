#!/usr/bin/env python3
"""Forged scientist: edmond_halley · lab environmental"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "scientists")]

os.environ.setdefault("LAB_ID", "environmental")
os.environ.setdefault("PERSONAS_YAML", "personas/environmental_squad.yaml")

from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config("edmond_halley", overrides={"port": 5145})
app = create_agent_app(AGENT_CONFIG)

if __name__ == "__main__":
    run_agent(app, AGENT_CONFIG)
