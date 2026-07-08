#!/usr/bin/env python3
"""Forged scientist: navigation_in_1701_he_published_the_first_magnetic_declination_charts_isogonic_lines_for_the_atlantic_and_pacific_oceans_to_aid_maritime_navigation · lab environmental"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "scientists")]

os.environ.setdefault("LAB_ID", "environmental")
os.environ.setdefault("PERSONAS_YAML", "personas/environmental_squad.yaml")

from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config("navigation_in_1701_he_published_the_first_magnetic_declination_charts_isogonic_lines_for_the_atlantic_and_pacific_oceans_to_aid_maritime_navigation", overrides={"port": 5147})
app = create_agent_app(AGENT_CONFIG)

if __name__ == "__main__":
    run_agent(app, AGENT_CONFIG)
