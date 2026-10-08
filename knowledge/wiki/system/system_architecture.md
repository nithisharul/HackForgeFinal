---
type: system
id: system_architecture
title: System: architecture and dependencies
written_by: code
---
# System: architecture and dependencies

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Flow
- Claims and reference data are read from `data/raw/` (see [[data_claims]]).
- Five claim rules flag individual claims: [[R1]], [[R2]], [[R3]], [[R4]], [[R5]].
- An anomaly model compares each provider with same-specialty peers; a graph step finds provider networks; a prediction model estimates repeat risk. See [[system_models]].
- Signals are combined into one case per provider, scored and ranked. See [[system_scoring]].
- The Second Brain supplies precedents that adjust confidence, and stores every verdict.

## Current funnel
- 80,452 claims, 846 claim alerts, 34 cases.

## Components
- Pipeline: `backend/pipeline/` (rules, anomaly, graph, predict, run_all). Run offline.
- Second Brain: `backend/brain/` (wiki, retrieve, confidence, brief, llm).
- API: FastAPI in `backend/app/`. Interface: React in `frontend/`.
- Knowledge: markdown files in `knowledge/`; conventions in `knowledge/SCHEMA.md`.

## Dependencies
- Python: pandas, numpy, scikit-learn, networkx, igraph and leidenalg, FastAPI.
- LLM: any OpenAI-compatible endpoint; the default is a local Ollama model, so no data leaves the machine. Without an LLM the system runs from templates.
- No database; data is CSV and JSON, knowledge is markdown.
- Limits: [[system_limits]].
