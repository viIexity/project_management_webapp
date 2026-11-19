"""
Main entry point for NexusPM — Project Management Web Application
(DAG Dependencies, Team Workload, PERT Analysis, Critical Path Method, and RCPSP Optimization).
"""
from __future__ import annotations
import sys
from backend.app import app, run_server

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    run_server(host="127.0.0.1", port=port)
